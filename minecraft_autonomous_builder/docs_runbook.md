# Failure Runbook

## Resume build
- Call `POST /projects/{id}/resume` to load latest checkpoint.

## Stale reservations
- Run maintenance task that invokes `SpatialIndexService.release_stale_reservations()`.

## Vision failures
- If score < threshold, keep project in planning and re-run `POST /projects/{id}/plan` for flagged modules.
