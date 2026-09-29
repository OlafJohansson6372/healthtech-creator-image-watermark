from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from .infrai_images import InfraiImages


class AppointmentState(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PublishRequest(BaseModel):
    appointment_ref: str = Field(min_length=6, max_length=64)
    publish_id: str = Field(min_length=8, max_length=128)
    appointment_state: AppointmentState
    filename: str = Field(min_length=1, max_length=120)
    watermark_text: str = Field(min_length=1, max_length=80)
    position: str = "bottom-right"
    opacity: float = Field(default=0.72, ge=0.0, le=1.0)


class PublishResult(BaseModel):
    appointment_ref: str
    state: str
    image: dict[str, object]
    notification: str


class AppointmentNotReady(ValueError):
    pass


def publish_creator_image(
    request: PublishRequest, image_bytes: bytes, images: InfraiImages
) -> PublishResult:
    if request.appointment_state is not AppointmentState.CONFIRMED:
        raise AppointmentNotReady("Only confirmed appointments can publish creator images")

    uploaded = images.upload(image_bytes, request.filename)
    image_ref = str(uploaded["id"])
    processed = images.watermark(
        image=image_ref,
        text=request.watermark_text,
        position=request.position,
        opacity=request.opacity,
        publish_id=request.publish_id,
    )
    return PublishResult(
        appointment_ref=request.appointment_ref,
        state="published",
        image=processed,
        notification="Your appointment image is ready in the creator portal.",
    )

