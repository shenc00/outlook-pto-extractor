"""Load config.yaml (with optional config.local.yaml override)."""
from __future__ import annotations

import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path: str | None = None) -> dict:
    path = path or os.path.join(ROOT, "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    local = os.path.join(os.path.dirname(path), "config.local.yaml")
    if os.path.exists(local):
        with open(local, "r", encoding="utf-8") as f:
            _deep_merge(cfg, yaml.safe_load(f) or {})
    return cfg


def _deep_merge(base: dict, override: dict) -> dict:
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
    return base
