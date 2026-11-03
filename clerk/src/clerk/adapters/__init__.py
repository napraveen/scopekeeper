"""Adapters implementing ScopeKeeper port protocols."""

from clerk.adapters.clock import SimulatedClock, SystemClock, parse_clock_offset
from clerk.adapters.github import GitHubHostAdapter
from clerk.adapters.llm_providers import (
    AnthropicLLMAdapter,
    GeminiLLMAdapter,
    OpenAILLMAdapter,
    create_llm_adapter,
)
from clerk.adapters.llm_scripted import (
    RenewalGroupingOutput,
    RenewalThemeSpec,
    ScoutSplitOutput,
    ScriptedLLM,
)
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import FakePreview, LocalPreviewAdapter
from clerk.adapters.switch_inmemory import InMemoryRoomState, InMemorySwitch
from clerk.adapters.switch_protocol import SwitchBudgetExceededError, SwitchProtocolAdapter

__all__ = [
    "AnthropicLLMAdapter",
    "FakePreview",
    "GeminiLLMAdapter",
    "GitHubHostAdapter",
    "InMemoryRoomState",
    "InMemorySwitch",
    "LocalGitHost",
    "LocalPreviewAdapter",
    "OpenAILLMAdapter",
    "RenewalGroupingOutput",
    "RenewalThemeSpec",
    "ScoutSplitOutput",
    "ScriptedLLM",
    "SimulatedClock",
    "SwitchBudgetExceededError",
    "SwitchProtocolAdapter",
    "SystemClock",
    "create_llm_adapter",
    "parse_clock_offset",
]
