"""Shared pytest fixtures for Clerk tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from clerk.domain.models import (
    EnvelopeConfig,
    Plan,
    RateCardConfig,
    RoomsConfig,
    ScheduleConfig,
    ScopeMapConfig,
    SeedLedgerConfig,
)
from clerk.settings import ConfigBundle, load_all_configs


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Return the repository root path."""
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def config_dir(repo_root: Path) -> Path:
    """Return the path to the real config/ directory."""
    return repo_root / "config"


@pytest.fixture(scope="session")
def config_bundle(config_dir: Path) -> ConfigBundle:
    """Load and validate the real project configuration bundle."""
    return load_all_configs(config_dir)


@pytest.fixture(scope="session")
def scope_map(config_bundle: ConfigBundle) -> ScopeMapConfig:
    """Return the validated ScopeMapConfig."""
    return config_bundle.scope_map


@pytest.fixture(scope="session")
def rate_card(config_bundle: ConfigBundle) -> RateCardConfig:
    """Return the validated RateCardConfig."""
    return config_bundle.rate_card


@pytest.fixture(scope="session")
def plan(config_bundle: ConfigBundle) -> Plan:
    """Return the validated Plan."""
    return config_bundle.plan


@pytest.fixture(scope="session")
def envelope_config(config_bundle: ConfigBundle) -> EnvelopeConfig:
    """Return the validated EnvelopeConfig."""
    return config_bundle.envelope


@pytest.fixture(scope="session")
def schedule_config(config_bundle: ConfigBundle) -> ScheduleConfig:
    """Return the validated ScheduleConfig."""
    return config_bundle.schedule


@pytest.fixture(scope="session")
def rooms_config(config_bundle: ConfigBundle) -> RoomsConfig:
    """Return the validated RoomsConfig."""
    return config_bundle.rooms


@pytest.fixture(scope="session")
def seed_ledger(config_bundle: ConfigBundle) -> SeedLedgerConfig:
    """Return the validated SeedLedgerConfig."""
    return config_bundle.seed_ledger
