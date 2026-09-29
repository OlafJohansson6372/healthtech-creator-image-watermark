from __future__ import annotations

import os

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from .appointment_workflow import (
    AppointmentNotReady,
    AppointmentState,
    PublishRequest,
    PublishResult,
    publish_creator_image,
)
from .infrai_images import InfraiError, InfraiImages

app = FastAPI(title="Health creator image publisher")


@app.post("/appointments/creator-image", response_model=PublishResult)
def publish_image(
    image: UploadFile = File(),
    appointment_ref: str = Form(),
    publish_id: str = Form(),
    appointment_state: AppointmentState = Form(),
    watermark_text: str = Form(),
    position: str = Form("bottom-right"),
    opacity: float = Form(0.72),
) -> PublishResult:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="INFRAI_API_KEY is not configured")

    request = PublishRequest(
        appointment_ref=appointment_ref,
        publish_id=publish_id,
        appointment_state=appointment_state,
        filename=image.filename or "creator-image.jpg",
        watermark_text=watermark_text,
        position=position,
        opacity=opacity,
    )
    try:
        return publish_creator_image(request, image.file.read(), InfraiImages(api_key))
    except AppointmentNotReady as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": exc.details.get("message", str(exc))},
        ) from exc
