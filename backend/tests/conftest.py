import pytest

from app.services.mami_config import load_mami_config


@pytest.fixture(scope="session")
def mami_codes() -> list[str]:
    """Real MAMI code IDs from config/mami-framework.json, for use as synthetic scoring input."""
    return [c["id"] for c in load_mami_config()["codes"]]


@pytest.fixture
def make_answers(mami_codes):
    """Build a list of synthetic answer dicts for the scoring engine.

    Cycles through real MAMI codes and a fixed rotation of answer values so
    the ZEN decision table exercises COMPLIANT / FINDING / NOT_APPLICABLE paths.
    """
    values = ["YES", "NOT_THERE_YET", "NOT_APPLICABLE"]

    def _make(count: int) -> list[dict]:
        answers = []
        for i in range(count):
            code = mami_codes[i % len(mami_codes)]
            answers.append(
                {
                    "mami_code": code,
                    "moscow_level": "MUST" if i % 2 == 0 else "SHOULD",
                    "answer_value": values[i % len(values)],
                    "critical_override": None,
                }
            )
        return answers

    return _make
