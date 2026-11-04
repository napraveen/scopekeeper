"""FastAPI application factory for ScopeKeeper Clerk."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from clerk.adapters.clock import SimulatedClock, SystemClock
from clerk.adapters.github import GitHubHostAdapter
from clerk.adapters.llm_providers import create_llm_adapter
from clerk.adapters.local_git import LocalGitHost
from clerk.adapters.preview_local import FakePreview, LocalPreviewAdapter
from clerk.adapters.switch_inmemory import InMemorySwitch
from clerk.adapters.switch_protocol import SwitchProtocolAdapter
from clerk.api.auth import APIError, http_exception_to_error_payload
from clerk.api.routes import router as api_router
from clerk.api.sse import EventBroadcaster
from clerk.db.repositories import LedgerRepository
from clerk.db.session import create_db_engine, create_session_factory, init_db, reset_and_seed_db
from clerk.ports.protocols import ClockPort, GitHostPort, LLMPort, PreviewPort, SwitchPort
from clerk.services.workflow import WorkflowOrchestrator
from clerk.settings import ConfigBundle, Settings, load_all_configs
from clerk.workers.switch_consumer import SwitchConsumerWorker
from clerk.workers.timeouts import EstimatorTimeoutWorker


def _resolve_default_config_dir(settings: Settings) -> Path:
    for candidate in (
        settings.clerk_config_dir,
        Path("./config"),
        Path("../config"),
        Path(__file__).resolve().parents[4] / "config",
    ):
        if candidate.exists() and (candidate / "scope-map.yaml").exists():
            return candidate.resolve()
    return settings.clerk_config_dir


def create_app(
    *,
    settings: Settings | None = None,
    config: ConfigBundle | None = None,
    repo: LedgerRepository | None = None,
    switch: SwitchPort | None = None,
    llm: LLMPort | None = None,
    git_host: GitHostPort | None = None,
    preview: PreviewPort | None = None,
    clock: ClockPort | None = None,
    start_workers: bool = False,
) -> FastAPI:
    """Create and configure the Clerk FastAPI application."""
    cfg_settings = settings or Settings()
    cfg_bundle = config or load_all_configs(_resolve_default_config_dir(cfg_settings))

    active_clock: ClockPort = clock or (
        SimulatedClock(cfg_settings.clock_start, cfg_bundle.schedule.agency_timezone)
        if cfg_settings.demo_mode
        else SystemClock(cfg_bundle.schedule.agency_timezone)
    )

    broadcaster = EventBroadcaster()

    if repo is None:
        engine = create_db_engine(cfg_settings.database_url)
        init_db(engine)
        session_factory = create_session_factory(engine)
        repo = LedgerRepository(
            session_factory,
            default_plan=cfg_bundle.plan,
            on_event=broadcaster.publish,
        )
        if not repo.list_asks():
            reset_and_seed_db(engine, cfg_bundle.seed_ledger, cfg_bundle.plan)
    else:
        repo.set_on_event(broadcaster.publish)

    active_switch: SwitchPort
    if switch is not None:
        active_switch = switch
    elif cfg_settings.clerk_api_key and cfg_settings.clerk_api_key != "dev-agent-token":
        active_switch = SwitchProtocolAdapter(
            base_url=cfg_settings.switch_base_url,
            ws_url=cfg_settings.switch_ws_url,
            agent_id=cfg_settings.clerk_agent_id,
            api_key=cfg_settings.clerk_api_key,
            rooms_config=cfg_bundle.rooms,
            clock=active_clock,
        )
    else:
        active_switch = InMemorySwitch(rooms_config=cfg_bundle.rooms, clock=active_clock)

    active_llm: LLMPort = llm or create_llm_adapter(cfg_settings)
    active_git: GitHostPort = git_host or (
        GitHubHostAdapter(repo=cfg_settings.github_repo, token=cfg_settings.github_token)
        if cfg_settings.git_host == "github" and cfg_settings.github_token
        else LocalGitHost(repo_path=cfg_settings.demo_repo_path)
    )
    active_preview: PreviewPort = preview or (
        LocalPreviewAdapter(base_url=cfg_settings.preview_base_url)
        if start_workers
        else FakePreview(base_url=cfg_settings.preview_base_url)
    )

    orchestrator = WorkflowOrchestrator(
        config=cfg_bundle,
        repo=repo,
        switch=active_switch,
        llm=active_llm,
        git_host=active_git,
        preview=active_preview,
        clock=active_clock,
    )

    consumer_worker = SwitchConsumerWorker(
        switch=active_switch,
        orchestrator=orchestrator,
    )
    timeout_worker = EstimatorTimeoutWorker(cr_service=orchestrator.cr_service)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if start_workers:
            orchestrator.scheduler.start()
            await consumer_worker.start()
            await timeout_worker.start()
        try:
            yield
        finally:
            broadcaster.close_all()
            if start_workers:
                await timeout_worker.stop()
                await consumer_worker.stop()
                orchestrator.scheduler.stop()

    app = FastAPI(
        title="ScopeKeeper Clerk API",
        version="0.1.0",
        docs_url="/docs",
        lifespan=lifespan,
    )

    app.state.settings = cfg_settings
    app.state.admin_token = cfg_settings.admin_token
    app.state.config = cfg_bundle
    app.state.repo = repo
    app.state.orchestrator = orchestrator
    app.state.broadcaster = broadcaster

    raw_origins = [o.strip() for o in cfg_settings.cors_origins.split(",") if o.strip()]
    allowed_origins = list(
        dict.fromkeys(["http://localhost:5173", "http://localhost:3000", *raw_origins])
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(APIError)
    async def handle_api_error(_req: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(_req: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=http_exception_to_error_payload(exc),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _req: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": str(exc.errors()),
                }
            },
        )

    @app.get("/", response_class=HTMLResponse)
    async def get_index() -> str:
        return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>ScopeKeeper Clerk</title>
    <style>
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; display: flex; justify-content: center; }
      .card { max-width: 650px; width: 100%; background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2rem; box-shadow: 0 10px 25px rgba(0,0,0,0.3); }
      h1 { font-size: 1.75rem; margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 0.5rem; }
      p { color: #94a3b8; line-height: 1.6; }
      .badge { display: inline-block; background: #0369a1; color: #e0f2fe; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
      .links { margin-top: 1.5rem; display: grid; gap: 0.75rem; }
      .btn { display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: #334155; color: #f8fafc; text-decoration: none; border-radius: 8px; font-weight: 500; transition: background 0.2s; }
      .btn:hover { background: #475569; }
      .btn-primary { background: #2563eb; }
      .btn-primary:hover { background: #1d4ed8; }
      .meta { font-size: 0.8rem; color: #64748b; margin-top: 1.5rem; text-align: center; }
    </style>
  </head>
  <body>
    <div class="card">
      <span class="badge">ScopeKeeper Live</span>
      <h1>🛡️ ScopeKeeper Clerk Backend</h1>
      <p>The multi-agent scope-to-delivery governance backend on Switch is active and listening on port 8080.</p>
      
      <div class="links">
        <a class="btn btn-primary" href="/docs" target="_blank">
          <span>📚 Open Interactive API (Swagger UI)</span>
          <span>&rarr;</span>
        </a>
        <a class="btn" href="/api/public/co/CR-002" target="_blank">
          <span>📄 View Client Change Order (CR-002)</span>
          <span>&rarr;</span>
        </a>
        <a class="btn" href="/api/health" target="_blank">
          <span>💓 System Health & Simulated Clock</span>
          <span>&rarr;</span>
        </a>
        <a class="btn" href="/api/desk" target="_blank">
          <span>🕒 Desk State (@client-desk / The Flip)</span>
          <span>&rarr;</span>
        </a>
        <a class="btn" href="/api/overview" target="_blank">
          <span>📊 Monthly KPIs & Overview (Bearer auth)</span>
          <span>&rarr;</span>
        </a>
        <a class="btn" href="/api/rooms" target="_blank">
          <span>🗺️ Room Topology & Links (React Flow)</span>
          <span>&rarr;</span>
        </a>
      </div>
      <div class="meta">Flip the Switch Hackathon (Track 1: Best Business Workflow)</div>
    </div>
  </body>
</html>"""

    app.include_router(api_router)
    return app


def get_default_app() -> FastAPI:
    """ASGI entrypoint for `uvicorn clerk.main:app`."""
    return create_app(start_workers=False)


app: Any = None
