# Minecraft Autonomous Builder

Implementation of the AGENT.md blueprint: a dual-agent Plan → Execute → Verify pipeline with persistent MemPalace state, schematic generation, execution checkpoints, and vision verification.

## Quick start

```bash
cp .env.example .env
make setup
make init-db
make test
make run-api
```

## API flow
1. `POST /projects`
2. `POST /projects/{project_id}/plan`
3. `POST /projects/{project_id}/execute`
4. `POST /projects/{project_id}/verify`
5. `POST /projects/{project_id}/resume` (if needed)

## Notes
- Bot and world-edit adapters are implemented with production contracts and safe defaults.
- Live Minecraft/Ollama integration requires external services configured in `.env`.
- Data is persisted in `data/mempalace.db`.
