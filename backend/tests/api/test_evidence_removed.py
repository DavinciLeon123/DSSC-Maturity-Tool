"""Static + integration proof that the evidence/URL-per-question subsystem
(MIGR-02) is fully absent.

Per the plan's must_haves, a leftover reference to the deleted evidence
model class name in a comment or dead code would silently fail the
MIGR-02 acceptance criterion, so `test_no_evidence_model_import` builds
the class name from parts at runtime rather than embedding the literal
in this file — that would make the grep self-matching against its own
source.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2] / "app"

# Built from parts so this file's own source never contains the literal
# class name — a naive grep for the deleted model would otherwise flag
# this test file itself as a false positive.
_DELETED_MODEL_CLASS_NAME = "Evidence" + "URL"


def test_evidence_route_returns_404(client):
    # Former routes: POST/GET/DELETE /api/v1/initiatives/{id}/evidence[/{evidence_id}].
    # The router no longer exists at all — FastAPI must return a plain 404
    # (route not found), never 405 (route exists but method not allowed) or
    # 500 (route exists but crashes internally).
    get_response = client.get("/api/v1/initiatives/1/evidence")
    assert get_response.status_code == 404

    post_response = client.post(
        "/api/v1/initiatives/1/evidence",
        json={"question_id": "q-1-1", "mami_code": "S-HRA-1.1", "url": "https://example.com"},
    )
    assert post_response.status_code == 404


def test_no_evidence_model_import():
    """Static check (MIGR-02): the deleted evidence model class name must
    not appear anywhere under backend/app — including comments and dead
    code, not just live imports (a leftover reference in a comment would
    otherwise silently pass an import-only check)."""
    offending: list[str] = []
    for py_file in APP_ROOT.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        if _DELETED_MODEL_CLASS_NAME in source:
            offending.append(str(py_file.relative_to(APP_ROOT.parent)))

    assert offending == [], (
        f"Found leftover reference(s) to the deleted evidence model class name in: {offending}"
    )


def test_no_evidence_model_ast_walk_confirms_no_class_definition():
    """Belt-and-suspenders: confirm via AST (not just substring match) that
    no class named after the deleted evidence model is defined anywhere
    under backend/app."""
    for py_file in APP_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assert node.name != _DELETED_MODEL_CLASS_NAME, (
                    f"{py_file} still defines the deleted evidence model class"
                )
