from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import requests
import re
import json
import logging

logger = logging.getLogger("planner_service")
logging.basicConfig(level=logging.INFO)

class PlanRequest(BaseModel):
    prompt: str
    model: Optional[str] = None

app = FastAPI(title="Planner & Critic Service")


@app.post("/plan")
def plan_endpoint(req: PlanRequest):
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = req.model or os.environ.get("OLLAMA_MODEL", "ministral-14b:latest")
    build_system_prompt = os.environ.get(
        "BUILD_SYSTEM_PROMPT",
        "You are a strict JSON generator. Reply with ONLY a single JSON object and NOTHING else. The object must match the BuildTask schema."
    )

    full_prompt = f"{build_system_prompt}\n\n{req.prompt}"
    try:
        r = requests.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": full_prompt, "max_tokens": 800},
            timeout=60,
        )
    except Exception as e:
        logger.exception("Failed to reach Ollama")
        raise HTTPException(status_code=502, detail=f"Failed to reach Ollama: {str(e)}")

    if r.status_code >= 400:
        logger.warning("Ollama responded %s: %s", r.status_code, r.text[:200])
        raise HTTPException(status_code=502, detail=f"Ollama error: {r.status_code}")

    raw = r.text or ""
    try:
        body_json = r.json()
        if isinstance(body_json, dict) and "text" in body_json and isinstance(body_json["text"], str):
            raw = body_json["text"]
    except Exception:
        pass

    def sanitize(s: str) -> str:
        s = s.lstrip("\ufeff")
        s = re.sub(r"```(?:json)?\r?\n([\s\S]*?)```", r"\1", s, flags=re.IGNORECASE)
        s = re.sub(r"```([\s\S]*?)```", r"\1", s)
        return s.strip()

    text = sanitize(raw)

    def extract_json(s: str):
        s = s.strip()
        # try whole text
        try:
            return json.loads(s)
        except Exception:
            pass

        # balanced-brace scan
        stack = []
        start_idx = None
        for i, ch in enumerate(s):
            if ch == '{':
                if start_idx is None:
                    start_idx = i
                stack.append(i)
            elif ch == '}' and stack:
                stack.pop()
                if not stack and start_idx is not None:
                    candidate = s[start_idx:i+1]
                    try:
                        return json.loads(candidate)
                    except Exception:
                        pass

        # regex fallback
        m = re.search(r"(\{[\s\S]*\})", s)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass
        return None

    parsed = extract_json(text)
    if parsed is None:
        logger.warning("Failed to extract JSON from Ollama response")
        return {"ok": False, "error": "no_json", "raw": text[:2000]}

    return {"ok": True, "task": parsed, "raw": text[:2000]}


@app.post("/critique")
def critique_endpoint(payload: dict):
    # Minimal scaffold: implement critique/repair workflow here.
    return {"ok": True, "critique": "not implemented - scaffold only"}
