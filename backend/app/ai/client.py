import json
import logging
import re
import time

import httpx
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import LLMError, LLMNotConfigured
from app.models import AIUsageLog

logger = logging.getLogger(__name__)
PENDING_USAGE: list[dict] = []


def drain_usage() -> list[dict]:
    items = list(PENDING_USAGE)
    PENDING_USAGE.clear()
    return items


def parse_json_content(content: str) -> dict:
    text = (content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError("模型输出不是有效的 JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("模型输出不是 JSON 对象")
    return data


class LLMClient:
    async def complete_json(self, system: str, user: str, task_id: str, user_id: int) -> dict:
        if not settings.llm_api_key:
            raise LLMNotConfigured()
        url = settings.llm_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.llm_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        last_error: Exception | None = None
        started = time.perf_counter()
        response_json = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    response = await client.post(url, json=payload, headers=headers)
                if response.status_code >= 500:
                    raise LLMError("模型服务暂时不可用，请稍后重试")
                if response.status_code >= 400:
                    logger.info("llm status=%s task=%s", response.status_code, task_id)
                    raise LLMError("模型接口拒绝了请求")
                response_json = response.json()
                break
            except (httpx.TimeoutException, httpx.TransportError, LLMError) as exc:
                last_error = exc
                if isinstance(exc, LLMError) and "拒绝" in str(exc):
                    self._log_usage(task_id, user_id, 0, 0, started, "failed")
                    raise
                if attempt == 2:
                    self._log_usage(task_id, user_id, 0, 0, started, "failed")
                    if isinstance(exc, LLMError):
                        raise
                    raise LLMError("模型服务暂时不可用，请稍后重试") from exc
        if response_json is None:
            raise LLMError() from last_error
        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            self._log_usage(task_id, user_id, 0, 0, started, "failed")
            raise LLMError("模型输出缺少内容") from exc
        usage = response_json.get("usage") or {}
        self._log_usage(
            task_id,
            user_id,
            int(usage.get("prompt_tokens") or 0),
            int(usage.get("completion_tokens") or 0),
            started,
            "success",
        )
        logger.info(
            "llm ok task=%s input_chars=%s output_chars=%s",
            task_id,
            len(user),
            len(content or ""),
        )
        return parse_json_content(content)

    def _log_usage(self, task_id: str, user_id: int, prompt_tokens: int, completion_tokens: int, started: float, status: str) -> None:
        PENDING_USAGE.append(
            {
                "task_id": task_id,
                "user_id": user_id,
                "model": settings.llm_model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "status": status,
            }
        )


def get_llm_client() -> LLMClient:
    return LLMClient()


_writing_usage = False


@event.listens_for(Session, "before_flush")
def _flush_usage(session: Session, _flush_context, _instances) -> None:
    global _writing_usage
    if _writing_usage:
        return
    items = drain_usage()
    if not items:
        return
    _writing_usage = True
    try:
        for item in items:
            session.add(AIUsageLog(**item))
    finally:
        _writing_usage = False
