# Failure Runbook — Minecraft Autonomous Builder

## 1. Resume Interrupted Build

**Symptom:** Build process crashed or was killed mid-execution.

**Recovery:**
```bash
# Resume from latest checkpoint
curl -X POST http://localhost:8080/projects/{project_id}/resume
```

**Verification:**
```bash
# Check build log for latest checkpoint
curl http://localhost:8080/projects/{project_id}/state
```
Verify `checkpoint_state.batch_index` matches expected resume point. No duplicate batches should be placed.

---

## 2. Stale Coordinate Reservations

**Symptom:** Module reservations stuck in `reserved` state after a crash.

**Recovery:**
```python
from mempalace.accessor import MemPalaceAccessor
from mempalace.spatial_index import SpatialIndexService

accessor = MemPalaceAccessor("./data/mempalace.db")
spatial = SpatialIndexService(accessor.repo, stale_minutes=30)
spatial.release_stale_reservations()
```

**Verification:**
```sql
SELECT * FROM coord_index WHERE reservation_status = 'reserved' AND reserved_at < datetime('now', '-30 minutes');
```
Should return 0 rows after cleanup.

---

## 3. Vision Verification Failures

**Symptom:** LLaVA score < 80 for one or more modules.

**Recovery:**
1. The orchestrator automatically writes `vision_critique_vN` to MemPalace.
2. Call `POST /projects/{id}/plan` to trigger re-entry for flagged modules only.
3. After re-approval, call `POST /projects/{id}/execute` to rebuild only the affected modules.

**Verification:**
```bash
curl http://localhost:8080/projects/{project_id}/state | jq '.vision_critiques'
```

---

## 4. Crash/Restart Recovery

**Symptom:** API server or bot process crashed mid-pipeline.

**Recovery:**
1. Restart the API server: `uvicorn src.api.app:app --host 0.0.0.0 --port 8080`
2. Restart the bot: `node dist/index.js`
3. Check readiness: `curl http://localhost:8080/health/ready`
4. Resume the build: `curl -X POST http://localhost:8080/projects/{project_id}/resume`

**Verification:**
- Check `/health/ready` returns `"status": "ready"`
- Verify checkpoint chain in `build_log` table has no gaps
- Confirm `projects.status` matches expected phase

---

## 5. Database Corruption Recovery

**Symptom:** SQLite errors, `database disk image is malformed`.

**Recovery:**
```bash
# Backup corrupt database
cp data/mempalace.db data/mempalace.db.corrupt

# Re-initialize from scratch
python scripts/init_db.py

# Re-import from backup if available (blueprint exports)
python scripts/export_blueprint.py --project-id {project_id} --output backup.json
```

**Prevention:**
- Ensure `MEMPALACE_BUSY_TIMEOUT_MS=5000` is set to handle concurrent writes
- Run regular SQLite integrity checks: `sqlite3 data/mempalace.db "PRAGMA integrity_check;"`

---

## 6. Ollama/LLM Service Unavailable

**Symptom:** Planning loop returns `"status": "failed"` with LLM timeout errors.

**Recovery:**
```bash
# Check Ollama status
curl http://127.0.0.1:11434/api/tags

# Restart Ollama
ollama serve &

# Pull required model if missing
ollama pull llava:latest
ollama pull qwen3-14b

# Re-run planning
curl -X POST http://localhost:8080/projects/{project_id}/plan
```

**Fallback:** Agents automatically fall back to deterministic planners when LLM is unavailable.

---

## 7. WorldEdit Paste Failure

**Symptom:** Batch execution returns `status: "failed"` with WorldEdit errors.

**Recovery:**
1. Check schematic file exists: `ls data/schematics/{project_id}/`
2. Verify Minecraft server is running with WorldEdit/FAWE plugin
3. Check bot connectivity: `curl http://127.0.0.1:3001/health`
4. Resume from last successful checkpoint:
   ```bash
   curl -X POST http://localhost:8080/projects/{project_id}/resume
   ```

**Common errors:**
- `schem load` fails: schematic file not in WorldEdit's schematic directory
- `paste` fails: insufficient permissions or protected region

---

## 8. Bot Disconnected / Reconnection

**Symptom:** Bot not responding to commands, checkpoint events not arriving.

**Recovery:**
```bash
# Restart bot
cd bot && npm run build && node dist/index.js

# Verify connection
curl http://127.0.0.1:3001/health

# Check bot logs for Minecraft connection errors
```

**Common issues:**
- Minecraft server not running or not on LAN
- Wrong host/port in `bot/config.json`
- Authentication mode mismatch (ensure `auth: "offline"` for offline mode/TLauncher)

---

## 9. Disk Space Exhaustion

**Symptom:** API returns 500 errors, database writes fail.

**Recovery:**
```bash
# Check disk usage
du -sh data/schematics/ data/screenshots/ data/mempalace.db

# Clean old screenshots
rm -rf data/screenshots/*/

# Clean old schematic versions (keep latest)
find data/schematics/ -name "*_v*.schem" -mtime +7 -delete

# Vacuum SQLite to reclaim space
sqlite3 data/mempalace.db "VACUUM;"
```

---

## 10. Schema Validation Failures

**Symptom:** Planning loop returns `"status": "failed"` with `schema_validation_error`.

**Recovery:**
1. Check architect agent logs for the exact validation error
2. Verify `schemas/blueprint_module.schema.json` matches expected contract
3. If schema changed, re-run planning:
   ```bash
   curl -X POST http://localhost:8080/projects/{project_id}/plan
   ```

---

## 11. Coordinate Collision During Planning

**Symptom:** Planning loop returns `"status": "failed"` with `coordinate_collision`.

**Recovery:**
1. Check which modules are colliding:
   ```sql
   SELECT project_id, module_name, x, y, z FROM coord_index WHERE reservation_status = 'reserved';
   ```
2. Release stale reservations (see Section 2)
3. Re-run planning

---

## 12. Network Partition (API ↔ Bot)

**Symptom:** Bot API commands return `dispatch_failed` or connection refused.

**Recovery:**
```bash
# Test connectivity
curl http://127.0.0.1:3001/health

# Check bot is listening on expected port
netstat -tlnp | grep 3001

# Restart bot if needed
node dist/index.js

# Verify API can reach bot
curl http://localhost:8080/health/ready | jq '.checks.bot_api'
```

---

## One-Command Local Bring-Up

```bash
# Using docker-compose (recommended)
docker compose up --build -d

# Or manually
cp .env.example .env
make setup
make init-db
make run-api
# In separate terminal:
cd bot && npm run build && node dist/index.js
```

## Health Check Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health/live` | Process liveness (PID check) |
| `GET /health/ready` | Full dependency health (DB, Ollama, bot, disk) |
| `GET /projects/{id}/state` | Project state snapshot |
