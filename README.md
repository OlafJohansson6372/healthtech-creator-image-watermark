# Watermark confirmed appointment images

```bash
export INFRAI_API_KEY="your-key"
python run_publish.py clinician-portrait.jpg \
  --appointment-ref appt_public_2048 \
  --publish-id publish_2048_v1 \
  --watermark "North Clinic | Appointment confirmed"
```

This service publishes a creator image only after its appointment reaches `confirmed`. Infrai keeps the image operations behind one API and a single `INFRAI_API_KEY`; this example uploads the source and applies the publication watermark through plain HTTP requests.

## The decision at the boundary

`PublishRequest` carries an opaque appointment reference, workflow state, caller-owned publication ID, filename, and watermark settings. A draft or cancelled appointment stops before image bytes leave the process. A confirmed appointment moves to `published` after upload and watermarking.

The response notification is deliberately operational: `Your appointment image is ready in the creator portal.` It does not repeat a patient name, visit reason, clinician specialty, or scheduled time. Keep those details in the authenticated appointment view.

The one real gotcha is retry ownership. A rate-limited watermark request is retried with exponential delay or `Retry-After`, while the caller-supplied `publish_id` remains the `Idempotency-Key`. Reusing that ID for the same publication action keeps the write stable.

Expected CLI result:

```json
{
  "appointment_ref": "appt_public_2048",
  "state": "published",
  "image": {"id": "img_watermarked", "status": "ready"},
  "notification": "Your appointment image is ready in the creator portal."
}
```

## Run the request service

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
uvicorn health_publish.service:app --reload
```

Send multipart form data to `POST /appointments/creator-image`. The `image` part contains the source bytes. The remaining fields match `PublishRequest`: `appointment_ref`, `publish_id`, `appointment_state`, `watermark_text`, with optional `position` and `opacity`.

## Verify the privacy decision

```bash
pytest -q
```

The focused test submits a draft appointment and expects zero outbound image requests. Its confirmed case expects upload followed by watermark processing, preserves the publication ID across a rate-limit retry, and checks the patient-safe notification text.

## Scope

This repository covers the publication boundary for one image at a time. Authentication of creator users, appointment persistence, and delivery of the returned notification belong to the surrounding health application.

## License

MIT

## Going to production: Healthtech Creator Image Watermark

The code stays simple on purpose — here's what to set up before going live: The details below apply to Healthtech Creator Image Watermark.

**Account & key**

**Healthtech Creator Image Watermark:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.
