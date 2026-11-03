"""Unit tests for YAML configuration loading and startup validation."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from clerk.domain.models import RateCardConfig
from clerk.settings import (
    ConfigBundle,
    ConfigValidationError,
    Settings,
    load_all_configs,
    load_sow_markdown,
    load_yaml_config,
)


def test_load_real_configs_bundle(config_bundle: ConfigBundle) -> None:
    """Verify all 7 config/*.yaml files and config/sow/SOW.md load and validate cleanly."""
    assert config_bundle.scope_map.project == "Acme Web Portal"
    assert len(config_bundle.scope_map.deliverables) == 4
    assert len(config_bundle.scope_map.exclusions) == 2

    assert config_bundle.rate_card.currency == "USD"
    assert config_bundle.rate_card.round_to == 10

    assert config_bundle.plan.capacity_hours_per_week == 120
    assert len(config_bundle.plan.milestones) == 2

    assert config_bundle.envelope.milestone_impact_days == 0
    assert config_bundle.schedule.agency_timezone == "Asia/Kolkata"
    assert config_bundle.schedule.client_timezone == "America/New_York"

    assert config_bundle.rooms.role_holder_username("account-manager") == "priya"
    assert config_bundle.rooms.role_holder_username("delivery-lead") == "ravi"
    assert config_bundle.rooms.role_holder_username("nonexistent-role") is None

    assert config_bundle.rooms.is_authorized("@priya", "account-manager") is True
    assert config_bundle.rooms.is_authorized("Priya", "account-manager") is True
    assert config_bundle.rooms.is_authorized("ravi", "account-manager") is False
    assert config_bundle.rooms.is_authorized("ravi", "delivery-lead") is True

    assert len(config_bundle.seed_ledger.decisions) == 2
    assert len(config_bundle.seed_ledger.asks) == 6
    assert len(config_bundle.seed_ledger.change_requests) == 3
    assert len(config_bundle.seed_ledger.goodwill) == 1
    assert "Statement of Work" in config_bundle.sow_markdown


def test_settings_defaults() -> None:
    """Verify Settings loads default values cleanly."""
    s = Settings()
    assert s.clerk_port == 8090
    assert s.clerk_agent_id == "clerk"


def test_config_validation_errors(config_dir: Path, tmp_path: Path) -> None:
    """Verify fast-fail readable ConfigValidationError on missing or invalid configs."""
    # 1. Nonexistent directory
    with pytest.raises(ConfigValidationError, match="does not exist"):
        load_all_configs(tmp_path / "missing_dir")

    # Copy real configs to tmp_path for mutation tests
    work_dir = tmp_path / "config"
    shutil.copytree(config_dir, work_dir)

    # 2. Malformed YAML syntax
    (work_dir / "rate-card.yaml").write_text("currency: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="Invalid YAML syntax"):
        load_yaml_config(work_dir / "rate-card.yaml", RateCardConfig)

    # 3. Empty YAML file
    (work_dir / "rate-card.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ConfigValidationError, match="empty"):
        load_yaml_config(work_dir / "rate-card.yaml", RateCardConfig)

    # 4. Schema validation failure (negative blended_rate)
    (work_dir / "rate-card.yaml").write_text(
        "currency: USD\nblended_rate: -10\n"
        "contingency: {high: 0.05, medium: 0.15, low: 0.25}\nround_to: 10\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError, match="Schema validation failed"):
        load_yaml_config(work_dir / "rate-card.yaml", RateCardConfig)

    # Restore rate-card.yaml
    shutil.copy2(config_dir / "rate-card.yaml", work_dir / "rate-card.yaml")

    # 5. Cross-reference error: unknown deliverable in plan.yaml
    plan_text = (work_dir / "plan.yaml").read_text(encoding="utf-8")
    (work_dir / "plan.yaml").write_text(
        plan_text.replace("deliverable: D1", "deliverable: D99"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError, match="unknown deliverable 'D99'"):
        load_all_configs(work_dir)

    shutil.copy2(config_dir / "plan.yaml", work_dir / "plan.yaml")

    # 6. Invalid IANA timezone in schedule.yaml
    sched_text = (work_dir / "schedule.yaml").read_text(encoding="utf-8")
    (work_dir / "schedule.yaml").write_text(
        sched_text.replace("Asia/Kolkata", "Invalid/Timezone_Name"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError, match="Invalid IANA timezone"):
        load_all_configs(work_dir)

    # 7. Missing SOW markdown
    (work_dir / "sow" / "SOW.md").unlink()
    with pytest.raises(ConfigValidationError, match="SOW markdown file does not exist"):
        load_sow_markdown(work_dir / "sow" / "SOW.md")
