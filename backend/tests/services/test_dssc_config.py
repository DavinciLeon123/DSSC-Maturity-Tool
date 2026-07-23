"""Unit tests for load_dssc_questionnaire_config() (backend/app/services/mami_config.py).

Covers QSTN-01 (52 questions), QSTN-03 (per-question options override,
no hardcoded content in Python), QSTN-05 (structural skeleton is real-size,
content is pure data). No HTTP/DB dependency — this loader is a plain
file-I/O read, so tests call it directly.
"""

import json
from pathlib import Path

from app.services.mami_config import CONFIG_DIR, load_dssc_questionnaire_config

CONFIG_PATH = Path(CONFIG_DIR) / "dssc-questionnaire.json"


def test_all_52_questions_present():
    # QSTN-01/QSTN-05: exactly 52 questions across exactly 6 categories.
    config = load_dssc_questionnaire_config()

    assert len(config["categories"]) == 6
    total_questions = sum(len(cat["questions"]) for cat in config["categories"])
    assert total_questions == 52


def test_config_is_pure_data_no_hardcoded_labels():
    # QSTN-03/D-09: every question resolves to exactly 5 options scored 1-5.
    # Questions without their own `options` inherit `default_options`; the one
    # override question returns its own 5 options instead.
    config = load_dssc_questionnaire_config()

    default_options = config["default_options"]
    assert len(default_options) == 5
    assert [o["score"] for o in default_options] == [1, 2, 3, 4, 5]

    override_count = 0
    for category in config["categories"]:
        for question in category["questions"]:
            options = question.get("options", default_options)
            assert len(options) == 5
            assert [o["score"] for o in options] == [1, 2, 3, 4, 5]
            if "options" in question:
                override_count += 1
                # The override question must carry its own distinct labels,
                # not a coincidental copy of the shared defaults.
                assert options != default_options

    assert override_count == 1


def test_served_content_is_byte_for_parsed_equal_to_raw_json_file():
    # Proves no hardcoded question/label strings leak from Python: the
    # loader's return value must be exactly what's on disk, parsed, with
    # zero transformation/branching applied.
    raw = json.loads(CONFIG_PATH.read_text())
    served = load_dssc_questionnaire_config()

    assert served == raw
