"""Az OpenAPI export (a 03 §5.1a).

**A specifikáció a KÓDBÓL jön** (a 03 §5.1a: "a `response_model` NEM
kézzel írt másolat — a DB-sémából generálódik") → **a FastAPI
automatikusan generálja** → **ez a modul kiírja a
`docs/api/v1/openapi.json`-ba** (a `packages/api-client` innen
generálódik).

Az OpenAPI export adatbázis-kapcsolat nélkül működik.
"""

from __future__ import annotations

import json
import sys

from duna.main import app


def main() -> int:
    """Az OpenAPI séma kiírása a stdout-ra."""
    schema = app.openapi()
    json.dump(schema, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
