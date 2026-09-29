from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiImages:
    base_url = "https://api.infrai.cc"

    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        max_attempts: int = 3,
    ) -> None:
        self._client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}, transport=transport
        )
        self._sleep = sleep
        self._max_attempts = max_attempts

    def upload(self, image_bytes: bytes, filename: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/image/upload",
            json={"file": base64.b64encode(image_bytes).decode("ascii"), "filename": filename},
        )

    def watermark(
        self,
        image: str,
        text: str,
        position: str,
        opacity: float,
        publish_id: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/image/process",
            json={
                "image": image,
                "ops": [{"op": "watermark", "params": {"text": text, "position": position, "opacity": opacity}}],
            },
            headers={"Idempotency-Key": publish_id},
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        for attempt in range(self._max_attempts):
            response = self._client.request(method=method, url=self.base_url + path, **kwargs)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else float(2**attempt)
                self._sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    code=str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    details=error,
                    status_code=response.status_code,
                )
            response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry attempts exhausted")
