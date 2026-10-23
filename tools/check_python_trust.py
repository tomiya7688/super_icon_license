"""Verify the Python packaging/tooling trust stores used by this repository.

This is intentionally small and dependency-free so CI can run it immediately after
upgrading pip and certifi.
"""
from __future__ import annotations

import importlib.metadata
import re
import ssl
import subprocess
import tempfile
from pathlib import Path

import certifi

MIN_PIP = (26, 2, 2)
MIN_CERTIFI = (2026, 10, 19)

# The emergency response removes trust paths related to the compromised G3 chain.
BLOCKED_SUBJECT_MARKERS = (
    "emSign ECC Root CA - G3",
    "emSign Root TLS CA - G3",
)


def numeric_version(value: str) -> tuple[int, ...]:
    parts = [int(part) for part in re.findall(r"\d+", value)]
    return tuple(parts)


def require_version(name: str, current: str, minimum: tuple[int, ...]) -> None:
    parsed = numeric_version(current)
    if parsed < minimum:
        raise SystemExit(
            f"{name} {current} is too old; require >= {'.'.join(map(str, minimum))}"
        )


def pem_blocks(path: Path) -> list[bytes]:
    data = path.read_bytes()
    return re.findall(
        rb"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----\s*",
        data,
        flags=re.DOTALL,
    )


def certificate_subjects(path: Path) -> list[str]:
    subjects: list[str] = []
    for block in pem_blocks(path):
        with tempfile.NamedTemporaryFile(suffix=".pem") as temp:
            temp.write(block)
            temp.flush()
            result = subprocess.run(
                ["openssl", "x509", "-in", temp.name, "-noout", "-subject"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        subjects.append(result.stdout.strip())
    return subjects


def verify_bundle(label: str, path: Path) -> None:
    if not path.exists():
        print(f"{label}: not present ({path})")
        return

    subjects = certificate_subjects(path)
    if not subjects:
        raise SystemExit(f"{label}: no PEM certificates found in {path}")

    blocked = [
        subject
        for subject in subjects
        if any(marker in subject for marker in BLOCKED_SUBJECT_MARKERS)
    ]
    if blocked:
        raise SystemExit(
            f"{label}: compromised emSign/eMudhra trust path still present in {path}: "
            + "; ".join(blocked)
        )

    print(f"{label}: {path} ({len(subjects)} certificates), blocked G3 trust absent")


def main() -> None:
    pip_version = importlib.metadata.version("pip")
    certifi_version = certifi.__version__
    require_version("pip", pip_version, MIN_PIP)
    require_version("certifi", certifi_version, MIN_CERTIFI)

    print(f"Python: {ssl.OPENSSL_VERSION}")
    print(f"pip: {pip_version}")
    print(f"certifi: {certifi_version}")

    certifi_path = Path(certifi.where()).resolve()
    verify_bundle("certifi bundle", certifi_path)

    paths = ssl.get_default_verify_paths()
    print(f"system verify paths: cafile={paths.cafile!r}, capath={paths.capath!r}")
    if paths.cafile:
        system_bundle = Path(paths.cafile).resolve()
        # Avoid scanning the same file twice on environments where Python is
        # configured to point directly at certifi.
        if system_bundle != certifi_path:
            verify_bundle("system CA bundle", system_bundle)


if __name__ == "__main__":
    main()
