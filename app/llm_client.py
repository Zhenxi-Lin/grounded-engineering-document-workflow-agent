from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DOTENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    model: str
    base_url: str
    timeout_seconds: float = 30.0


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    @classmethod
    def from_env(
        cls,
        prefixes: tuple[str, ...] = ("GROUNDED_QA_LLM", "OPENAI"),
    ) -> "LLMClient | None":
        load_project_dotenv()

        api_key = resolve_env_value(prefixes, "API_KEY", default="")
        model = resolve_env_value(prefixes, "MODEL", default="")
        base_url = resolve_env_value(prefixes, "BASE_URL", default="https://api.openai.com/v1")
        timeout_seconds = float(resolve_env_value(prefixes, "TIMEOUT", default="30"))

        if not api_key or not model:
            return None

        normalized_base_url = base_url.rstrip("/")
        return cls(
            LLMConfig(
                api_key=api_key,
                model=model,
                base_url=normalized_base_url,
                timeout_seconds=timeout_seconds,
            )
        )

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        try:
            response_payload = self._post_chat_completions(payload)
        except urllib.error.HTTPError as exc:
            if exc.code == 400:
                LOGGER.warning("LLM endpoint rejected response_format=json_object; retrying without it")
                payload.pop("response_format", None)
                response_payload = self._post_chat_completions(payload)
            else:
                raise

        content = extract_message_content(response_payload)
        return parse_json_object(content)

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.config.base_url}/chat/completions"
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


def extract_message_content(response_payload: dict[str, Any]) -> str:
    choices = response_payload.get("choices", [])
    if not choices:
        raise ValueError("LLM response does not contain choices")

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text", "")))
        return "\n".join(part for part in text_parts if part.strip())
    raise ValueError("Unsupported LLM message content format")


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = strip_code_fence(stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM output is not valid JSON")
        return json.loads(stripped[start : end + 1])


def strip_code_fence(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return text


def load_project_dotenv(dotenv_path: Path = DEFAULT_DOTENV_PATH) -> None:
    if not dotenv_path.exists():
        return

    loaded_keys = 0
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key or normalized_key in os.environ:
            continue

        os.environ[normalized_key] = normalize_dotenv_value(value.strip())
        loaded_keys += 1

    if loaded_keys:
        LOGGER.info("Loaded %s variable(s) from %s", loaded_keys, dotenv_path)


def normalize_dotenv_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {"'", '"'}:
        return stripped[1:-1]
    return stripped


def resolve_env_value(prefixes: tuple[str, ...], suffix: str, *, default: str) -> str:
    for prefix in prefixes:
        env_name = f"{prefix}_{suffix}"
        value = os.getenv(env_name)
        if value is not None and value.strip():
            return value.strip()
    return default
