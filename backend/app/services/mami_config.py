"""Questionnaire config loader utilities."""

import json
from pathlib import Path

# Resolve config dir relative to this file's location:
# services/ -> app/ -> backend/ -> repo root -> config/
CONFIG_DIR = Path(__file__).parent.parent.parent.parent / "config"


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


def load_dssc_questionnaire_config() -> dict:
    """Load config/dssc-questionnaire.json. Single universal 52-question /
    6-category config, no participant_type key (D-10, QSTN-04).

    WR-04: fails fast at startup (not at request time) if any category has
    zero questions. A zero-question category makes
    `compute_dimension_scores` emit a synthetic `0.0` score that falls
    below every `maturity_bands` entry's `min` (all start at 1.0),
    which `get_maturity_band` then raises `ValueError` on — a 500 on every
    report/heatmap request rather than a config-load error a maintainer
    sees immediately when editing the questionnaire.
    """
    path = CONFIG_DIR / "dssc-questionnaire.json"
    config = json.loads(path.read_text())
    empty_categories = [
        cat["id"] for cat in config.get("categories", []) if not cat.get("questions")
    ]
    if empty_categories:
        raise ValueError(
            "dssc-questionnaire.json has zero-question categories, which would "
            "produce an out-of-band 0.0 score no maturity_bands entry covers: "
            f"{empty_categories}. Add questions to these categories or remove "
            "them from the config entirely."
        )
    return config
