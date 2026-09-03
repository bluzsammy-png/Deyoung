# CI_CD — Continuous Integration & Delivery

PATI's CI/CD philosophy follows its architecture: **local-first, free-tier
only, boring on purpose.** The full pipeline runs on free CI (GitHub Actions
free tier for public repos) and, more importantly, is small enough to run
entirely on your machine.

## 1. The pipeline (definition)

```
on: push / pull_request
  ├─ 1. lint & types           (fast fail, < 1 min)
  ├─ 2. schema check           (gen_schemas.py reproducible, schemas valid)
  ├─ 3. unit + integration     (pytest, ~15 s, no network)
  ├─ 4. e2e smoke              (both flows against a booted server)
  └─ 5. registry audit         (every registry entry: cost ≤ 0, license present)
on: tag (v*)
  └─ 6. package & publish      (sdist/wheel + zip bundle artifact)
```

### Stage details

1. **Lint & types** — syntax/imports sanity; if a linter is configured
   (ruff), zero-warning policy on `pati_api/` and `pati_agent/` (the
   security-sensitive code).
2. **Schema check** — `python scripts/gen_schemas.py` must produce zero
   diffs (docs/schemas cannot drift), and every schema parses against draft
   2020-12.
3. **Tests** — the 46-test suite. Deliberately no network: connector tests
   use stubbed transports, Kaggle tests use fixture payloads. Tests that
   need a live GPU are not tests; they are the optional benchmark stage.
4. **E2E smoke** — boot `pati-server` on an ephemeral port, run
   `examples/e2e_demo.py` (disk flow; agent in-process) and
   `examples/e2e_remote_gpu.py` in *mock-GPU mode* (the example's
   degradation path asserts `RESOURCE_UNAVAILABLE` when no worker offers
   GPU — which is exactly what an empty CI runner provides for free).
5. **Registry audit** — a test asserts: every model entry has
   `cost ≤ 0` + license + source; every tool/capability maps to a registered
   worker or agent op; every connector declares its ToS/free-tier row.
   This is FREE_FIRST_POLICY enforced continuously.
6. **Package** — `python -m build` (sdist + wheel) and the delivery zip;
   attached to the GitHub Release. No paid registries; nothing auto-published
   to PyPI unless a maintainer adds trusted publishing later (still free).

## 2. Reference GitHub Actions workflow

```yaml
# .github/workflows/ci.yml  (conceptual reference; keep in sync)
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest        # free tier for public repos
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: python scripts/gen_schemas.py --check
      - run: python -m pytest tests -q
      - name: e2e smoke (disk flow + resource-unavailable path)
        run: |
          python pati_api/app.py &           # or: pati-server &
          sleep 2
          python examples/e2e_demo.py
          python examples/e2e_remote_gpu.py --expect-unavailable
  registry-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -e .
      - run: python -m pytest tests/test_registries.py tests/test_schemas.py -q
```

A Windows job (`windows-latest`, also free) can be added to run the
path-guard tests under Windows path semantics — recommended before each
release since the primary host is Windows.

## 3. Local equivalents (no CI account needed)

```bash
python scripts/gen_schemas.py --check     # schema drift
python -m pytest tests -q                 # suite
python examples/e2e_demo.py               # flow 1
python examples/e2e_remote_gpu.py         # flow 2 (or --expect-unavailable)
```

A single `make check` wraps all of the above (see `Makefile`).

## 4. Delivery packaging

The release artifact is a self-contained zip (source + docs + schemas +
installer). Producing it locally:

```bash
python scripts/package.py            # if present; else:
git archive --format=zip -o pati-<version>.zip HEAD
```

Contents checklist for a release zip:

- [ ] All source packages + `pyproject.toml`
- [ ] `schemas/` (normative)
- [ ] `docs/` complete (README doc map must resolve — no dead links)
- [ ] `installer/` + `examples/`
- [ ] `LICENSE` (MIT) and attribution section (LICENSE_POLICY §7)

## 5. Release procedure (maintainer)

1. `python -m pytest tests -q` green on the release commit.
2. Both examples pass on a real machine (Windows preferred).
3. Bump version in `pyproject.toml` (SemVer), tag `vX.Y.Z`.
4. Package zip + sdist/wheel; attach to the release.
5. Release notes: features / fixes / security notes / registry additions
   with license-cost rows (OPEN_SOURCE_POLICY §6).

## 6. What CI deliberately does not do

- **No deploy step.** PATI deploys by "run the installer on your PC" —
  there is no server to push to and no keys to leak (DEPLOYMENT §8).
- **No GPU runners.** Free CI has none; GPU work is validated by the
  Kaggle worker's own smoke run on a maintainer machine before tag.
- **No secrets in CI.** The suite runs token-less by design; if a test
  needs a token it mints one from the API under test.
- **No paid services anywhere**, including "free for OSS" tiers that
  require a payment method on file — that's a FREE_FIRST violation.
