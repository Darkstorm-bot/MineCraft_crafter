from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import httpx
from mempalace.accessor import MemPalaceAccessor
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .build_resume import BuildResumeService
from .worldedit_adapter import PasteCommand, WorldEditAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BatchResult:
    batch_index: int
    blocks_placed: int
    status: str
    error: str | None = None
    retry_count: int = 0


class BatchBuilderService:
    """Executes approved blueprint modules in batches with checkpoint and resume support."""

    def __init__(
        self,
        accessor: MemPalaceAccessor,
        adapter: WorldEditAdapter | None = None,
        bot_api_url: str | None = None,
    ):
        self.accessor = accessor
        self.adapter = adapter or WorldEditAdapter()
        self.bot_api_url = bot_api_url or os.getenv("BOT_API_URL", "http://127.0.0.1:3001")
        self.resume_service = BuildResumeService(accessor)
        self._http_client = httpx.Client(timeout=30.0)

    def _send_command(self, command: str, module_name: str) -> dict:
        """Dispatch a WorldEdit command to the Minecraft bot via HTTP API."""
        try:
            resp = self._http_client.post(
                f"{self.bot_api_url}/command",
                json={"command": command, "module": module_name},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Bot API command dispatch failed: %s", exc)
            return {"status": "dispatch_failed", "error": str(exc)}
        except Exception as exc:
            logger.warning("Bot API command dispatch failed: %s", exc)
            return {"status": "dispatch_failed", "error": str(exc)}

    def _get_completed_batches(self, project_id: str) -> set[int]:
        """Retrieve set of already-completed batch indices for a project."""
        latest = self.accessor.get_latest_checkpoint(project_id)
        if latest is None:
            return set()
        return set(latest["checkpoint_state"].get("completed_batches", []))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError),
        reraise=True,
    )
    def _dispatch_with_retry(self, command: str, module_name: str) -> dict:
        """Dispatch command with automatic retry on transient failures."""
        result = self._send_command(command, module_name)
        if result.get("status") == "dispatch_failed":
            raise httpx.HTTPError(result["error"])
        return result

    def execute(
        self,
        project_id: str,
        blueprint_id: str,
        modules: list[dict],
        batch_size: int = 500,
        resume: bool = True,
    ) -> list[BatchResult]:
        """Execute modules in batches, writing checkpoints after each.

        If resume=True, skips already-completed batches based on latest checkpoint.
        """
        results: list[BatchResult] = []
        completed_batches = set()

        # Resume support: skip already-completed batches
        if resume:
            completed_batches = self._get_completed_batches(project_id)
            if completed_batches:
                logger.info("Resuming build: skipping batches %s", completed_batches)

        # Group modules into batches
        batch_index = 0
        current_batch: list[dict] = []
        batch_groups: list[list[dict]] = []

        for module in modules:
            current_batch.append(module)
            if len(current_batch) >= batch_size:
                batch_groups.append(current_batch)
                current_batch = []
            batch_index += 1

        if current_batch:
            batch_groups.append(current_batch)

        # Execute each batch
        total_blocks_placed = 0
        for batch_idx, batch_modules in enumerate(batch_groups):
            # Skip completed batches during resume
            if batch_idx in completed_batches:
                logger.info("Skipping already-completed batch %d", batch_idx)
                continue

            batch_result = self._execute_batch(
                project_id, blueprint_id, batch_idx, batch_modules, completed_batches
            )
            results.append(batch_result)
            total_blocks_placed += batch_result.blocks_placed

            if batch_result.status != "ok":
                logger.error("Batch %d failed: %s", batch_idx, batch_result.error)
                break

        logger.info("Batch execution complete: %d blocks placed", total_blocks_placed)
        return results

    def _execute_batch(
        self,
        project_id: str,
        blueprint_id: str,
        batch_index: int,
        modules: list[dict],
        completed_so_far: set[int],
    ) -> BatchResult:
        """Execute a single batch of modules and write checkpoint."""
        total_blocks = 0
        retry_count = 0
        last_error: str | None = None
        status = "ok"

        for module in modules:
            module_name = module["module_name"]
            schematic_path = module.get("schematic_path", "unknown.schem")
            origin = module["bounds"]["min"]

            # Build WorldEdit paste command
            paste_cmd = PasteCommand(schematic_path=schematic_path, origin=origin)
            command_str = self.adapter.build_paste_command(paste_cmd)

            # Dispatch to bot
            try:
                result = self._dispatch_with_retry(command_str, module_name)
                if result.get("status") != "ok":
                    status = "retry"
                    last_error = result.get("error", "unknown")
                    retry_count += 1
                    logger.warning("Module %s dispatch returned non-ok: %s", module_name, last_error)
            except httpx.HTTPError as exc:
                status = "failed"
                last_error = str(exc)
                retry_count += 1
                logger.error("Module %s dispatch failed after retries: %s", module_name, exc)
                break

            blocks_placed = len(module["block_data"])
            total_blocks += blocks_placed

        # Write checkpoint after batch (atomic upsert)
        checkpoint = {
            "project_id": project_id,
            "blueprint_id": blueprint_id,
            "batch_index": batch_index,
            "blocks_placed": total_blocks,
            "status": status,
            "checkpoint_state": {
                "blueprint_id": blueprint_id,
                "batch_index": batch_index,
                "completed_batches": list(completed_so_far | {batch_index}),
                "current_origin": modules[-1]["bounds"]["min"] if modules else {"x": 0, "y": 0, "z": 0},
                "inventory_snapshot": {
                    k: v for mod in modules for k, v in mod.get("material_manifest", {}).items()
                },
                "retry_count": retry_count,
                "last_error": last_error,
            },
        }
        self.accessor.upsert_build_log(checkpoint)

        return BatchResult(
            batch_index=batch_index,
            blocks_placed=total_blocks,
            status=status,
            error=last_error,
            retry_count=retry_count,
        )
