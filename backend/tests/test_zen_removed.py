"""Static proof that the ZEN/MoSCoW scoring subsystem (SCOR-03, D-01) is
fully absent.

Mirrors Phase 13's `tests/api/test_evidence_removed.py` AST-walk /
substring-scan pattern. Scans `backend/app/` and `config/` only — never
`backend/tests/` — so this file's own source (which necessarily names the
removed symbols to search for them) can never self-match. Search tokens are
still built from parts, per that same precedent, as an extra guard against a
future refactor accidentally widening the scan to include this directory.
"""

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"
CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"
PYPROJECT_PATH = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Built from parts so this file's own source never contains the literal
# removed symbols as contiguous strings — belt-and-suspenders even though
# the scan below never touches backend/tests/ (Phase 13 precedent).
_ZEN_IMPORT = "import" + " zen"
_GET_ZEN_ENGINE = "get_" + "zen_engine"
_GET_MAMI_CONFIG = "get_" + "mami_config"
_LOAD_MAMI_CONFIG = "load_" + "mami_config"
_GET_SCORING_DIR = "get_" + "scoring_dir"
_SCORING_ENGINE_MODULE = "scoring" + "_engine"
_ZEN_ENGINE_CTOR = "zen" + ".ZenEngine"
_APP_STATE_ZEN_ENGINE = "app.state." + "zen_engine"
_APP_STATE_MAMI_CONFIG = "app.state." + "mami_config"
_ZEN_ENGINE_DEP_NAME = "zen" + "-engine"

_REMOVED_SYMBOL_TOKENS = {
    "the `zen` module import": _ZEN_IMPORT,
    "the get_zen_engine dependency": _GET_ZEN_ENGINE,
    "the get_mami_config dependency": _GET_MAMI_CONFIG,
    "the load_mami_config loader": _LOAD_MAMI_CONFIG,
    "the get_scoring_dir helper": _GET_SCORING_DIR,
    "the scoring_engine module reference": _SCORING_ENGINE_MODULE,
    "the zen.ZenEngine constructor call": _ZEN_ENGINE_CTOR,
    "the app.state.zen_engine assignment": _APP_STATE_ZEN_ENGINE,
    "the app.state.mami_config assignment": _APP_STATE_MAMI_CONFIG,
}

# Deliberately NOT included: a bare "mami_config" scan — mami_config.py
# survives with legitimate load_dssc_questionnaire_config/
# load_questionnaire_config(s) loaders (D-01 prohibition).


def _iter_py_files():
    for root in (APP_ROOT, CONFIG_ROOT):
        if root.exists():
            yield from root.rglob("*.py")


def test_no_removed_zen_moscow_symbols_in_app_or_config():
    """Every removed ZEN/MoSCoW symbol must be absent from backend/app and
    config/ — including comments and dead code, not just live imports (a
    leftover reference in a comment would otherwise silently pass an
    import-only check)."""
    offending: dict[str, list[str]] = {}
    py_files = list(_iter_py_files())
    for label, token in _REMOVED_SYMBOL_TOKENS.items():
        hits = []
        for py_file in py_files:
            source = py_file.read_text(encoding="utf-8")
            if token in source:
                hits.append(str(py_file.relative_to(APP_ROOT.parent.parent)))
        if hits:
            offending[label] = hits

    assert offending == {}, f"Found leftover ZEN/MoSCoW references: {offending}"


def test_no_zen_moscow_function_definitions_via_ast_walk():
    """Belt-and-suspenders: confirm via AST (not just substring match) that
    none of the removed dependency/loader functions are defined anywhere
    under backend/app."""
    removed_function_names = {
        _GET_ZEN_ENGINE,
        _GET_MAMI_CONFIG,
        _LOAD_MAMI_CONFIG,
        _GET_SCORING_DIR,
    }
    for py_file in APP_ROOT.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                assert node.name not in removed_function_names, (
                    f"{py_file} still defines the removed function {node.name!r}"
                )


def test_deleted_zen_moscow_files_do_not_exist():
    """The ZEN service module and both MAMI/MoSCoW config files must no
    longer exist in the repo (SCOR-03, D-01)."""
    deleted_paths = [
        APP_ROOT / "services" / "scoring_engine.py",
        CONFIG_ROOT / "scoring" / "mami-scoring.json",
        CONFIG_ROOT / "mami-framework.json",
    ]
    still_present = [str(p) for p in deleted_paths if p.exists()]
    assert still_present == [], f"Found files that should have been deleted: {still_present}"


def test_zen_engine_dependency_absent_from_pyproject():
    """The zen-engine PyPI package must no longer be declared as a
    dependency in backend/pyproject.toml."""
    source = PYPROJECT_PATH.read_text(encoding="utf-8")
    assert _ZEN_ENGINE_DEP_NAME not in source, (
        f"backend/pyproject.toml still declares the {_ZEN_ENGINE_DEP_NAME} dependency"
    )
