"""Environment settings and YAML configuration loader with strict startup validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from clerk.domain.models import (
    EnvelopeConfig,
    Plan,
    RateCardConfig,
    RoomsConfig,
    ScheduleConfig,
    ScopeMapConfig,
    SeedLedgerConfig,
)


class ConfigValidationError(Exception):
    """Raised when a configuration file is missing, malformed, or fails validation."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"Configuration error in {path}: {message}")


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Switch connection
    switch_url: str = "http://localhost:8700"
    switch_agent_token: str = "dev-agent-token"
    switch_admin_token: str = "dev-admin-token"
    clerk_agent_id: str = "clerk"
    clerk_display_name: str = "Clerk"
    clerk_model_name: str = "claude-sonnet-4-6"

    # LLM provider for classification & brief phrasing
    clerk_provider: Literal["anthropic", "openai", "google", "offline"] = "offline"
    clerk_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Clerk HTTP server & storage
    clerk_host: str = "0.0.0.0"
    clerk_port: int = 8090
    clerk_db_path: Path = Path("./data/clerk.db")
    clerk_config_dir: Path = Path("../config")
    clerk_log_level: str = "INFO"

    # Demo controls
    clerk_demo_clock: bool = True
    clerk_demo_token: str = "scopekeeper-demo"

    # Target codebase for Estimator & Builder
    target_repo_path: Path = Path("../target-repo")
    github_token: str = ""
    github_repo: str = ""


@dataclass(frozen=True)
class ConfigBundle:
    """Validated bundle of all ScopeKeeper project configuration files."""

    config_dir: Path
    scope_map: ScopeMapConfig
    rate_card: RateCardConfig
    plan: Plan
    envelope: EnvelopeConfig
    schedule: ScheduleConfig
    rooms: RoomsConfig
    seed_ledger: SeedLedgerConfig
    sow_markdown: str


def load_yaml_file(path: Path) -> Any:
    """Load a YAML file safely using ruamel.yaml."""
    if not path.exists():
        raise ConfigValidationError(path, "File does not exist.")
    if not path.is_file():
        raise ConfigValidationError(path, "Path is not a regular file.")

    yaml = YAML(typ="safe")
    try:
        raw_text = path.read_text(encoding="utf-8")
        data = yaml.load(raw_text)
    except YAMLError as exc:
        raise ConfigValidationError(path, f"Invalid YAML syntax: {exc}") from exc
    except OSError as exc:
        raise ConfigValidationError(path, f"Cannot read file: {exc}") from exc

    if data is None:
        raise ConfigValidationError(path, "YAML file is empty.")
    return data


def load_yaml_config[TModel: BaseModel](path: Path, model_cls: type[TModel]) -> TModel:
    """Load and validate a YAML file against a Pydantic schema."""
    data = load_yaml_file(path)
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise ConfigValidationError(path, f"Schema validation failed ({details})") from exc


def load_sow_markdown(path: Path) -> str:
    """Load the signed Statement of Work markdown file."""
    if not path.exists() or not path.is_file():
        raise ConfigValidationError(path, "SOW markdown file does not exist.")
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigValidationError(path, f"Cannot read SOW markdown: {exc}") from exc
    if not content:
        raise ConfigValidationError(path, "SOW markdown file is empty.")
    return content


def _validate_cross_references(
    config_dir: Path,
    scope_map: ScopeMapConfig,
    plan: Plan,
    schedule: ScheduleConfig,
) -> None:
    """Validate cross-file invariants (deliverable IDs and IANA timezones)."""
    deliverable_ids = {d.id for d in scope_map.deliverables}
    for milestone in plan.milestones:
        for item in milestone.items:
            if item.deliverable not in deliverable_ids:
                raise ConfigValidationError(
                    config_dir / "plan.yaml",
                    f"Plan item '{item.id}' references unknown deliverable '{item.deliverable}' "
                    f"(expected one of {sorted(deliverable_ids)}).",
                )

    for tz_field, tz_name in (
        ("agency_timezone", schedule.agency_timezone),
        ("client_timezone", schedule.client_timezone),
    ):
        try:
            ZoneInfo(tz_name)
        except ZoneInfoNotFoundError as exc:
            raise ConfigValidationError(
                config_dir / "schedule.yaml",
                f"Invalid IANA timezone for {tz_field}: '{tz_name}'.",
            ) from exc


def load_all_configs(config_dir: Path) -> ConfigBundle:
    """Load and validate all YAML config files and SOW.md from config_dir."""
    resolved_dir = config_dir.resolve()
    if not resolved_dir.exists() or not resolved_dir.is_dir():
        raise ConfigValidationError(config_dir, "Configuration directory does not exist.")

    scope_map = load_yaml_config(resolved_dir / "scope-map.yaml", ScopeMapConfig)
    rate_card = load_yaml_config(resolved_dir / "rate-card.yaml", RateCardConfig)
    plan = load_yaml_config(resolved_dir / "plan.yaml", Plan)
    envelope = load_yaml_config(resolved_dir / "envelope.yaml", EnvelopeConfig)
    schedule = load_yaml_config(resolved_dir / "schedule.yaml", ScheduleConfig)
    rooms = load_yaml_config(resolved_dir / "rooms.yaml", RoomsConfig)
    seed_ledger = load_yaml_config(resolved_dir / "seed-ledger.yaml", SeedLedgerConfig)
    sow_markdown = load_sow_markdown(resolved_dir / "sow" / "SOW.md")

    _validate_cross_references(resolved_dir, scope_map, plan, schedule)

    return ConfigBundle(
        config_dir=resolved_dir,
        scope_map=scope_map,
        rate_card=rate_card,
        plan=plan,
        envelope=envelope,
        schedule=schedule,
        rooms=rooms,
        seed_ledger=seed_ledger,
        sow_markdown=sow_markdown,
    )
