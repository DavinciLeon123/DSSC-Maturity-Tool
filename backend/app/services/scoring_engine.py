"""ZEN Engine scoring service — evaluates each answer individually using async_evaluate."""
import asyncio
import zen
from pathlib import Path
from app.services.mami_config import get_scoring_dir


def create_scoring_engine() -> zen.ZenEngine:
    """Create ZEN engine singleton with filesystem loader for config/scoring/*.json files."""
    scoring_dir = get_scoring_dir()

    def loader(key: str) -> str:
        return (scoring_dir / key).read_text()

    return zen.ZenEngine({"loader": loader})


async def score_all_answers(
    engine: zen.ZenEngine,
    answers: list[dict],
) -> list[dict]:
    """
    Score all answers using per-answer ZEN async evaluation.

    Each answer dict must contain:
      mami_code, moscow_level, answer_value, critical_override

    Returns only FINDING-status answers as a list of dicts:
      [{"mami_code": "S-HRA-1.1", "severity": "CRITICAL", "status": "FINDING"}, ...]

    Answers with status COMPLIANT or NOT_APPLICABLE are excluded from findings.
    """
    tasks = [
        engine.async_evaluate(
            "mami-scoring.json",
            {
                "answer": {
                    "mami_code": a["mami_code"],
                    "moscow_level": a["moscow_level"],
                    "answer_value": a["answer_value"],
                    "critical_override": a["critical_override"],
                }
            },
        )
        for a in answers
    ]

    results = await asyncio.gather(*tasks)

    findings = []
    for answer, result in zip(answers, results):
        outcome = result.get("result", {})
        if outcome.get("status") == "FINDING":
            findings.append({
                "mami_code": answer["mami_code"],
                "severity": outcome.get("severity", ""),
                "status": "FINDING",
            })
    return findings
