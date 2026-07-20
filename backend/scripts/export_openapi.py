"""Export the FastAPI OpenAPI schema to docs/api/openapi.json.

Run manually after changing routes/schemas: `uv run python scripts/export_openapi.py`
CI's docs-freshness gate re-runs this and fails the build on any diff (schema drift).
"""

import json
from pathlib import Path

from app.main import app

OUTPUT_PATH = Path(__file__).parent.parent.parent / "docs" / "api" / "openapi.json"


def main() -> None:
    schema = app.openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
