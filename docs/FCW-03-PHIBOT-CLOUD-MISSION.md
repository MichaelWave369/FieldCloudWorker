# FCW-03 | PhiBot delegated Scout mission observation

**Status:** Fixed scheduled observation / no autonomous PhiBot agent runtime.

A real GitHub Actions observation already performs public GitHub repository metadata inspection under the frozen `github_repo_metrics` task. FCW-03 produces a second *derived* evidence record without running a second task.

- Published path: `docs/phibot_mission.json`.
- Exact agent identity reference: `phibot.scout.cloud-review.v1`. This is a **planned** PhiBot identity namespace, not a registered PhiBot instance or authenticated principal.
- Mission ID: `phibot.scout.public-repo-health.v1`.
- Source task: `github_repo_metrics` only. No dynamic task selection.
- Workload: one already-completed fixed observation, zero model calls, zero network writes.
- Lifetime: 8 hours from source observation (source metadata, not a trusted clock).
- Source binding: SHA-256 of exact original status.json bytes; domain-separated SHA-256 of sidecar. These are content integrity hints, **not signatures**.
- Outcome: `OBSERVED_OK` or `OBSERVED_ERROR`; neither claims an agent made a decision.
- Publish gate: recompute entire sidecar from the sanitized status bytes; refuse drift, extra fields or local test run IDs.

This does not modify existing public observation status/history contracts, so other strict consumers remain compatible. The generated file appears only after the next real successful worker publish.

Next rung: PhiBot consumes this untrusted sidecar in a review-only adapter with exact identity/scope/expiry/source matching; a live inference/spawn runtime on a qualified host requires operator authorization and separate security testing.

Validation:

```
python -m unittest discover -s tests -v
```
