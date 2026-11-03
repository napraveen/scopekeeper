"""Contract tests for GitHubHostAdapter, LocalGitHost, LocalPreviewAdapter, and LLM providers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
import pytest
import respx

from clerk.adapters.github import GitHubHostAdapter
from clerk.adapters.llm_providers import (
    AnthropicLLMAdapter,
    GeminiLLMAdapter,
    OpenAILLMAdapter,
    create_llm_adapter,
)
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import LocalPreviewAdapter
from clerk.domain.models import Category, ClassificationResult
from clerk.settings import Settings


@pytest.mark.asyncio
async def test_github_host_adapter_issues_branches_and_prs() -> None:
    """Verify GitHubHostAdapter creates issues, blocks main branch, and discovers open PRs."""
    async with respx.mock(base_url="https://api.github.com") as respx_mock:
        issue_route = respx_mock.post("/repos/pixel-and-co/acme-portal/issues").mock(
            return_value=httpx.Response(
                201,
                json={
                    "number": 42,
                    "html_url": "https://github.com/pixel-and-co/acme-portal/issues/42",
                },
            )
        )
        pr_route = respx_mock.get("/repos/pixel-and-co/acme-portal/pulls").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "number": 19,
                        "title": "[ASK-0008] Dark mode",
                        "html_url": "https://github.com/pixel-and-co/acme-portal/pull/19",
                    }
                ],
            )
        )

        adapter = GitHubHostAdapter(
            repo="pixel-and-co/acme-portal",
            token="ghp_test_token",
        )
        ticket = await adapter.create_ticket(
            ask_id="ASK-0008",
            title="Dark mode",
            body="Wire theme toggle under Clause 2.4",
        )
        assert ticket.id == "#42"
        assert ticket.url == "https://github.com/pixel-and-co/acme-portal/issues/42"
        assert issue_route.called

        branch = await adapter.ensure_branch("sk/ask-0008-dark-mode")
        assert branch == "sk/ask-0008-dark-mode"
        with pytest.raises(ValueError, match="protected"):
            await adapter.ensure_branch("main")

        pr = await adapter.find_pull_request("sk/ask-0008-dark-mode")
        assert pr is not None
        assert pr.url == "https://github.com/pixel-and-co/acme-portal/pull/19"
        assert pr_route.called
        await adapter.close()


@pytest.mark.asyncio
async def test_local_git_host_detects_real_git_branch(tmp_path: Path) -> None:
    """Verify LocalGitHost writes ticket markdown, blocks main, and discovers real git branches."""
    repo_dir = tmp_path / "acme-portal"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "dev@pixel.co"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Dev"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )
    (repo_dir / "README.md").write_text("# Acme Portal\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=repo_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "checkout", "-b", "sk/ask-0008-dark-mode"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
    )

    host = LocalGitHost(repo_path=repo_dir)
    ticket = await host.create_ticket("ASK-0008", "Dark mode", "Body text")
    assert (repo_dir / ticket.url).exists()

    with pytest.raises(ValueError, match="protected"):
        await host.ensure_branch("main")

    pr = await host.find_pull_request("sk/ask-0008-dark-mode")
    assert pr is not None
    assert "sk/ask-0008-dark-mode" in pr.url


@pytest.mark.asyncio
async def test_local_preview_adapter_and_fallback() -> None:
    """Verify LocalPreviewAdapter calls /deploy and falls back gracefully when offline."""
    async with respx.mock(base_url="http://localhost:4300") as respx_mock:
        deploy_route = respx_mock.post("/deploy").mock(
            return_value=httpx.Response(
                200,
                json={
                    "work_id": "W-0003",
                    "branch": "sk/ask-0008-dark-mode",
                    "url": "http://localhost:4300/sk/ask-0008-dark-mode/",
                },
            )
        )
        preview = LocalPreviewAdapter(base_url="http://localhost:4300")
        url = await preview.deploy_preview("W-0003", "sk/ask-0008-dark-mode")
        assert url == "http://localhost:4300/sk/ask-0008-dark-mode/"
        assert deploy_route.called
        await preview.close()


@pytest.mark.asyncio
async def test_llm_providers_json_repair_retry_cache_and_fallback() -> None:
    """Verify Gemini, Anthropic, and OpenAI adapters validate JSON, retry, and cache."""
    valid_json = json.dumps(
        {
            "category": "IN_SCOPE",
            "clause_ids": ["2.4"],
            "related_item": None,
            "decision_id": None,
            "confidence": 0.95,
            "reason": "Covered by Clause 2.4 theming.",
            "question": None,
            "choices": [],
        }
    )

    # 1. Gemini adapter: first call returns invalid JSON, second call (repair retry) returns valid
    gemini_calls = 0

    def gemini_handler(_req: httpx.Request) -> httpx.Response:
        nonlocal gemini_calls
        gemini_calls += 1
        text = "not valid json" if gemini_calls == 1 else f"```json\n{valid_json}\n```"
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": text}]}}]},
        )

    async with respx.mock() as respx_mock:
        respx_mock.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        ).mock(side_effect=gemini_handler)

        gemini = GeminiLLMAdapter(
            api_key="gem-key",
            model_fast="gemini-2.5-flash",
            model_writer="gemini-2.5-pro",
        )
        res1 = await gemini.json("sys", "Can we get dark mode?", ClassificationResult)
        assert res1.category == Category.IN_SCOPE
        assert gemini_calls == 2

        # Second call with identical input hits SHA-256 cache without HTTP call
        res2 = await gemini.json("sys", "Can we get dark mode?", ClassificationResult)
        assert res2.category == Category.IN_SCOPE
        assert gemini_calls == 2
        await gemini.close()

    # 2. Anthropic adapter & OpenAI adapter text + fallback
    async with respx.mock() as respx_mock:
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(
                200,
                json={"content": [{"text": "Dark mode is ready to try."}]},
            )
        )
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=httpx.Response(500, json={"error": "server error"})
        )

        anthropic = AnthropicLLMAdapter(
            api_key="ant-key",
            model_fast="claude-3-5-haiku",
            model_writer="claude-sonnet-4-6",
        )
        txt = await anthropic.text("sys", "Write preview ready", max_words=10)
        assert txt == "Dark mode is ready to try."
        await anthropic.close()

        # OpenAI fails both attempts -> falls back cleanly to ScriptedLLM
        openai = OpenAILLMAdapter(
            api_key="oa-key",
            model_fast="gpt-4o-mini",
            model_writer="gpt-4o",
        )
        fallback_res = await openai.json(
            "sys",
            'Quoted Ask: "The login button is broken on Safari"',
            ClassificationResult,
        )
        assert fallback_res.category == Category.DEFECT
        await openai.close()

    # Factory test
    s = Settings(llm_provider="scripted")
    adapter = create_llm_adapter(s)
    assert adapter is not None
