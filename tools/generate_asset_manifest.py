"""Generate a deterministic provenance manifest and SHA-256 checksum list."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_revision() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=ROOT / "provenance" / "assets.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checksums", type=Path, required=True)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--revision", default=os.environ.get("GITHUB_SHA"))
    args = parser.parse_args()

    repository = args.repository or "local/unknown"
    revision = args.revision or git_revision()

    catalog_path = args.catalog if args.catalog.is_absolute() else ROOT / args.catalog
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assets = catalog.get("assets", [])
    if not assets:
        raise SystemExit("provenance catalog has no assets")

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    manifest_assets: list[dict[str, object]] = []
    checksum_lines: list[str] = []

    for item in assets:
        asset_id = item["id"]
        rel = item["path"]
        if asset_id in seen_ids:
            raise SystemExit(f"duplicate asset id: {asset_id}")
        if rel in seen_paths:
            raise SystemExit(f"duplicate asset path: {rel}")
        seen_ids.add(asset_id)
        seen_paths.add(rel)

        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"missing official asset: {rel}")

        digest = sha256(path)
        entry = dict(item)
        entry.update(
            {
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "source_revision": revision,
                "source_url": (
                    f"https://github.com/{repository}/blob/{revision}/"
                    f"{quote(rel, safe='/')}"
                ),
            }
        )
        manifest_assets.append(entry)
        checksum_lines.append(f"{digest} *{rel}")

    ids = {item["id"] for item in assets}
    for item in assets:
        parent = item.get("source_asset_id")
        if parent and parent not in ids:
            raise SystemExit(f"{item['id']}: unknown source_asset_id {parent}")

    catalog_digest = sha256(catalog_path)
    manifest = {
        "schema": "https://github.com/tomiya7688/asset-provenance/v1",
        "asset_set": catalog["asset_set"],
        "creator": catalog.get("creator"),
        "license": catalog["license"],
        "source_repository": f"https://github.com/{repository}",
        "source_revision": revision,
        "export_version": f"git-{revision[:12]}",
        "catalog_sha256": catalog_digest,
        "assets": manifest_assets,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.checksums.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.checksums.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"Generated manifest for {len(manifest_assets)} official assets at {revision}")


if __name__ == "__main__":
    main()
