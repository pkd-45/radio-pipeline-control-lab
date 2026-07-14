from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any


def sha256_file(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)


def product_record(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    return {"path": str(target), "bytes": target.stat().st_size, "sha256": sha256_file(target)}


def verify_products(products: list[dict[str, Any]]) -> bool:
    for product in products:
        path = Path(product["path"])
        if not path.exists() or sha256_file(path) != product["sha256"]:
            return False
    return True
