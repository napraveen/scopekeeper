"""Unit tests verifying Switch template validity, isolation, and parameters."""

from __future__ import annotations

import re
from pathlib import Path

from ruamel.yaml import YAML

from clerk.domain.models import SwitchTemplate

TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3] / "switch" / "templates" / "scopekeeper.template.yaml"
)


def test_switch_template_schema_and_integrity() -> None:
    """Verify that scopekeeper.template.yaml adheres to Switch template schema."""
    assert TEMPLATE_PATH.exists(), f"Template not found at {TEMPLATE_PATH}"

    yaml_parser = YAML(typ="safe")
    raw = yaml_parser.load(TEMPLATE_PATH.read_text(encoding="utf-8"))

    template = SwitchTemplate.model_validate(raw)
    assert template.version == 1
    assert template.group.name == "Acme Web Portal"
    assert template.group.color.startswith("#")

    # Verify parameters
    expected_params = {
        "client_bridge",
        "agency_bridge",
        "client_user",
        "account_manager",
        "delivery_lead",
        "reviewer",
        "clerk_agent",
    }
    for param in expected_params:
        assert param in template.params, f"Missing param: {param}"


def test_switch_template_agent_definitions_and_addressing() -> None:
    """Verify agents match Switch 0.31 protocol addressing rules and instructions."""
    yaml_parser = YAML(typ="safe")
    raw = yaml_parser.load(TEMPLATE_PATH.read_text(encoding="utf-8"))
    template = SwitchTemplate.model_validate(raw)

    agents_by_name = {a.name: a for a in template.agents}
    assert "acme-scout" in agents_by_name
    assert "acme-estimator" in agents_by_name
    assert "acme-builder" in agents_by_name

    # Scout must have addressing: anyone (to receive messages from client users)
    scout = agents_by_name["acme-scout"]
    assert scout.addressing == "anyone"
    assert "assume_role" in scout.instructions
    assert "client-desk" in scout.instructions

    # Estimator and Builder must have addressing: owner-agents (internal only)
    estimator = agents_by_name["acme-estimator"]
    assert estimator.addressing in {"owner_and_owner_agents", "owner-agents"}
    assert "Effort-Hours" in estimator.instructions
    assert "Never edit files" in estimator.instructions

    builder = agents_by_name["acme-builder"]
    assert builder.addressing in {"owner_and_owner_agents", "owner-agents"}
    assert "never push to main" in builder.instructions


def test_switch_template_room_isolation_and_governance() -> None:
    """Verify cross-company boundaries: Clerk, Estimator, and Builder are never in acme-client."""
    yaml_parser = YAML(typ="safe")
    raw = yaml_parser.load(TEMPLATE_PATH.read_text(encoding="utf-8"))
    template = SwitchTemplate.model_validate(raw)

    rooms_by_name = {r.name: r for r in template.rooms}
    assert {"acme-client", "acme-intake", "acme-delivery"}.issubset(rooms_by_name.keys())

    # 1. acme-client boundaries
    client_room = rooms_by_name["acme-client"]
    assert "acme-scout" in client_room.agents
    # CRITICAL: Clerk, Estimator, and Builder must NEVER join acme-client
    assert "{clerk_agent}" not in client_room.agents
    assert "clerk" not in client_room.agents
    assert "acme-estimator" not in client_room.agents
    assert "acme-builder" not in client_room.agents

    # Role client-desk must be exclusive
    client_roles = {r.name: r for r in client_room.roles}
    assert "client-desk" in client_roles
    assert client_roles["client-desk"].exclusive is True

    # Attached document scope-summary
    doc_names = [d.name for d in client_room.docs]
    assert "scope-summary" in doc_names

    # 2. acme-intake boundaries
    intake_room = rooms_by_name["acme-intake"]
    assert "acme-scout" in intake_room.agents
    assert "{clerk_agent}" in intake_room.agents
    assert "acme-estimator" not in intake_room.agents
    assert "acme-builder" not in intake_room.agents
    # Client user must NEVER be in intake
    assert "{client_user}" not in intake_room.users

    # 3. acme-delivery boundaries
    delivery_room = rooms_by_name["acme-delivery"]
    assert "{clerk_agent}" in delivery_room.agents
    assert "acme-estimator" in delivery_room.agents
    assert "acme-builder" in delivery_room.agents
    # Scout and client user are not in delivery
    assert "acme-scout" not in delivery_room.agents
    assert "{client_user}" not in delivery_room.users

    delivery_roles = {r.name: r for r in delivery_room.roles}
    assert "account-manager" in delivery_roles
    assert "delivery-lead" in delivery_roles


def test_switch_template_parameter_rendering() -> None:
    """Verify that substituting typical parameters leaves no unresolved template variables."""
    content = TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{client_bridge}": "discord-bridge",
        "{agency_bridge}": "slack-bridge",
        "{client_user}": "sam",
        "{account_manager}": "priya",
        "{delivery_lead}": "ravi",
        "{reviewer}": "aisha",
        "{clerk_agent}": "clerk",
        "{location}": "local",
        "{repo_dir}": "/opt/acme-portal",
    }
    rendered = content
    for pattern, value in replacements.items():
        rendered = rendered.replace(pattern, value)

    # Any leftover non-special single curly braces
    leftovers = re.findall(r"\{[a-zA-Z0-9_]+\}", rendered)
    # Filter out known Switch engine placeholders like {$agents_dir}
    unresolved = [m for m in leftovers if not m.startswith("{$")]
    assert not unresolved, f"Unresolved placeholders found in rendered template: {unresolved}"
