"""Gemeinsame Vorrichtungen für die Tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vocabmaster.config import Settings
from vocabmaster.database import Database
from vocabmaster.pack import Pack, scaffold

from .helpers import fill

REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def db() -> Database:
    return Database.load()


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def pack(db, settings) -> Pack:
    return Pack(data=fill(scaffold(db, 1, settings)))


@pytest.fixture
def pack_file(tmp_path, pack) -> Path:
    target = tmp_path / "unit_01.json"
    target.write_text(json.dumps(pack.data, ensure_ascii=False), encoding="utf-8")
    return target
