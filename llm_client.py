import hashlib
import json
import os
from datetime import datetime, timezone

from google import genai
from google.genai import types

import paths

MODEL = "gemini-2.5-flash"
_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("gemini_api")
        if not api_key:
            raise RuntimeError("gemini_api not set in environment")
        _client = genai.Client(api_key=api_key)
    return _client


def call(stage: str, prompt: str, input_artifacts: list[str], output_artifact: str) -> dict:
    client = _get_client()
    prompt_hash = "sha256:" + hashlib.sha256(prompt.encode()).hexdigest()

    def _invoke() -> dict:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            ),
        )
        return json.loads(response.text)

    try:
        result = _invoke()
    except json.JSONDecodeError:
        print(f"  [llm] JSON parse error on stage '{stage}', retrying...")
        result = _invoke()

    record = {
        "stage": stage,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "google",
        "model": MODEL,
        "prompt_hash": prompt_hash,
        "input_artifacts": input_artifacts,
        "output_artifact": output_artifact,
    }

    with open(paths.LLM_CALLS_LOG, "a") as f:
        f.write(json.dumps(record) + "\n")

    return result
