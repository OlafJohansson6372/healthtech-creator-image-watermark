from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from health_publish.appointment_workflow import (
    AppointmentState,
    PublishRequest,
    publish_creator_image,
)
from health_publish.infrai_images import InfraiImages


def main() -> None:
    parser = argparse.ArgumentParser(description="Watermark a confirmed appointment image")
    parser.add_argument("image", type=Path)
    parser.add_argument("--appointment-ref", required=True)
    parser.add_argument("--publish-id", required=True)
    parser.add_argument("--watermark", required=True)
    args = parser.parse_args()

    api_key = os.environ["INFRAI_API_KEY"]
    request = PublishRequest(
        appointment_ref=args.appointment_ref,
        publish_id=args.publish_id,
        appointment_state=AppointmentState.CONFIRMED,
        filename=args.image.name,
        watermark_text=args.watermark,
    )
    result = publish_creator_image(request, args.image.read_bytes(), InfraiImages(api_key))
    print(json.dumps(result.model_dump(), indent=2))


if __name__ == "__main__":
    main()

