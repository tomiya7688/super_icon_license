# Python TLS / CA security baseline

This repository contains a small Python image-processing utility. Following the
October 2026 eMudhra/emSign CA compromise, Python packaging and TLS tooling used
with this repository must meet the following baseline:

- `pip >= 26.2.2`
- `certifi >= 2026.10.19`
- if `uv` is introduced: `uv >= 0.13.4`
- if the Python `sigstore` package is introduced: `sigstore >= 4.5.1`

At the time this policy was added, this repository does **not** commit a virtual
environment, embedded Python runtime, Docker image, `uv` lock/configuration, or
Python `sigstore` dependency.

The GitHub Actions CI first upgrades Ubuntu `ca-certificates`, then upgrades pip and certifi on every run and executes
`tools/check_python_trust.py`. The checker records the active versions and
actual CA bundle paths, then verifies that the affected emSign/eMudhra G3 trust
path is not present in the certifi bundle or the system CA bundle used by
Python.

For a local environment, run:

```bash
python -m pip install --upgrade "pip>=26.2.2" "certifi>=2026.10.19"
python tools/check_python_trust.py
```

If a local venv, portable Python runtime, container, or build image is used,
perform the same check inside that environment. Rebuild disposable environments
rather than assuming that updating the source repository also updates an
already-created CA bundle.
