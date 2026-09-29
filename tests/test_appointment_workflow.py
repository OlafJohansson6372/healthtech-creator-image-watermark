import base64
import json

import httpx
import pytest

from health_publish.appointment_workflow import (
    AppointmentNotReady,
    AppointmentState,
    PublishRequest,
    publish_creator_image,
)
from health_publish.infrai_images import InfraiImages


def request(state: AppointmentState = AppointmentState.CONFIRMED) -> PublishRequest:
    return PublishRequest(
        appointment_ref="appt_public_2048",
        publish_id="publish_2048_v1",
        appointment_state=state,
        filename="clinician-portrait.jpg",
        watermark_text="North Clinic | Appointment confirmed",
    )


def test_draft_appointment_does_not_send_patient_image() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"ok": True, "data": {}})

    images = InfraiImages("test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(AppointmentNotReady):
        publish_creator_image(request(AppointmentState.DRAFT), b"private", images)
    assert calls == 0


def test_confirmed_appointment_uploads_then_watermarks_with_retry() -> None:
    seen: list[httpx.Request] = []
    sleeps: list[float] = []

    def handler(http_request: httpx.Request) -> httpx.Response:
        seen.append(http_request)
        if http_request.url.path == "/v1/image/upload":
            return httpx.Response(200, json={"ok": True, "data": {"id": "img_2048"}})
        if len(seen) == 2:
            return httpx.Response(
                429,
                headers={"Retry-After": "2"},
                json={"ok": False, "error": {"message": "retry"}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"id": "img_watermarked", "status": "ready"}},
        )

    images = InfraiImages(
        "test-key", transport=httpx.MockTransport(handler), sleep=sleeps.append
    )
    result = publish_creator_image(request(), b"jpeg-bytes", images)

    assert [item.url.path for item in seen] == [
        "/v1/image/upload",
        "/v1/image/process",
        "/v1/image/process",
    ]
    assert seen[0].headers["content-type"] == "application/json"
    assert json.loads(seen[0].content) == {
        "file": base64.b64encode(b"jpeg-bytes").decode("ascii"),
        "filename": "clinician-portrait.jpg",
    }
    payload = json.loads(seen[-1].content)
    assert payload == {
        "image": "img_2048",
        "ops": [{
            "op": "watermark",
            "params": {
                "text": "North Clinic | Appointment confirmed",
                "position": "bottom-right",
                "opacity": 0.72,
            },
        }],
    }
    assert seen[-1].headers["Idempotency-Key"] == "publish_2048_v1"
    assert sleeps == [2.0]
    assert result.state == "published"
    assert result.notification == "Your appointment image is ready in the creator portal."
