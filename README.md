# FieldCloudWorker v0.2

A small, governed cloud observation worker for the **Enter the Field** ecosystem. Adapted from Kimi's GitHub Actions scaffold and tested locally before initial deployment.

**Evidence is not authority.** This is not an autonomous LLM agent, a 24/7 service, a general-purpose code executor, or a route into private devices.

## Start the pilot

1. Review and merge the initial pull request.
2. Open repository Settings > Pages and select **GitHub Actions** as the deployment source.
3. Open Settings > Actions > General; the publisher needs **contents: write**. If branch protection blocks direct receipt commits, redesign publication to use a reviewed data branch rather than bypass protections.
4. Open Actions > **FieldCloudWorker Observation Pilot** > **Run workflow**.
5. When the publish job succeeds, visit https://michaelwave369.github.io/FieldCloudWorker/
6. Public data endpoints: https://michaelwave369.github.io/FieldCloudWorker/status.json and https://michaelwave369.github.io/FieldCloudWorker/history.jsonl

**There is intentionally no sample green status.** The dashboard shows a waiting state until a real cloud run publishes an observation.

## What it does

Every 6 hours (GitHub cron: minute 17) or by manual dispatch, a runner checks:
- A local heartbeat
- Presence of three required repository files
- Public GitHub repository issue/PR and star counts through a GET-only request

The observe job has only read permission. Its task allowlist is fixed in code. The independent publish job verifies exactly which receipt fields may be public, appends bounded history (30 summaries maximum), pushes only public data files, and explicitly deploys GitHub Pages.

Failed tasks are recorded without exception messages or tracebacks. The workflow finishes red **after** publishing the failure receipt, so the dashboard can show the issue.

## Local verification

Run these commands in the repo root:

    python -m unittest discover -s tests -v
    python worker/runner.py
    python worker/verify_receipt.py docs/status.json docs/history.jsonl
    python worker/check_health.py docs/status.json

Local runs cannot fetch repo metrics without GITHUB_REPOSITORY, so the third task records skipped_local. These commands generate data files locally.

## Architecture

GitHub schedule / manual dispatch
→ reviewed read-only task registry
→ bounded, schema-validated observation receipts
→ explicit GitHub Pages deployment
→ FieldDeck and FieldAccord consumers (future, review only)
→ separately authorized execution (never implicit)

GitHub Actions is **not guaranteed to run at exact times**. It can be delayed or dropped, and scheduled workflows may be disabled after inactivity. Automatic commits do not reliably prevent disablement. This pilot does not store secrets; all GitHub Pages data and public Actions logs are public.

## Future work

- Confirm the first real Actions run and Pages endpoint.
- Wire a read-only consumer into FieldDeck with explicit validation and a stale warning.
- Emit FieldAccord evidence packets without any implied permission.
- Require human review, explicit authorization, and a separate workflow for any side-effectful tasks.

See [FieldDeck](https://github.com/MichaelWave369/FieldDeck), [FieldAccord](https://github.com/MichaelWave369/FieldAccord), and [SuperPhiVessel](https://github.com/MichaelWave369/SuperPhiVessel).

Enter the Field. Carbon and silicon, building together.
