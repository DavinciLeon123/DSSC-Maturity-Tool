"""MAMI framework config loader utilities."""

import json
from pathlib import Path

# Resolve config dir relative to this file's location:
# services/ -> app/ -> backend/ -> repo root -> config/
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"


def load_mami_config() -> dict:
    """Load config/mami-framework.json. Returns full dict including version and codes list."""
    path = CONFIG_DIR / "mami-framework.json"
    return json.loads(path.read_text())


def load_questionnaire_config() -> dict:
    """Load config/questionnaire-v1.json. Returns full dict (legacy, kept for reference)."""
    path = CONFIG_DIR / "questionnaire-v1.json"
    return json.loads(path.read_text())


def load_questionnaire_configs() -> dict:
    """Load both DSI and SP questionnaire configs (v2).
    Returns dict keyed by participant_type: {"DSI": {...}, "SP": {...}}
    """
    dsi = json.loads((CONFIG_DIR / "dsi-questionnaire-v2.json").read_text())
    sp = json.loads((CONFIG_DIR / "sp-questionnaire-v2.json").read_text())
    return {"DSI": dsi, "SP": sp}


def get_scoring_dir() -> Path:
    """Return the path to config/scoring/ directory for ZEN engine loader."""
    return CONFIG_DIR / "scoring"
