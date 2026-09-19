import json

import httpx
import redis
from celery import shared_task
from django.conf import settings
from django.core.files.storage import default_storage
from google import genai
from .models import Job


def _publish(r, job_id, payload):
    r.publish(f"job:{job_id}", json.dumps(payload))


@shared_task
def process_pdf(job_id, storage_key):
    job = Job.objects.get(id=job_id)
    job.status = Job.PROCESSING
    job.save()

    r = redis.from_url(settings.CELERY_BROKER_URL)
    _publish(r, job_id, {"status": "PROCESSING", "step": "started"})

    try:
        with default_storage.open(storage_key, "rb") as f:
            extraction_response = httpx.post(
                f"{settings.PDF_EXTRACTION_SERVICE_URL}/extract",
                files={"file": f},
                timeout=60.0,
            )
        extraction_response.raise_for_status()
        record_id = extraction_response.json()["record_id"]
        _publish(r, job_id, {"status": "PROCESSING", "step": "extracted"})

        with default_storage.open(storage_key, "rb") as f:
            ingest_response = httpx.post(
                f"{settings.RAG_SEARCH_SERVICE_URL}/ingest/document",
                files={"file": f},
                timeout=300.0,
            )
        ingest_response.raise_for_status()

    except httpx.HTTPError as e:
        job.status = Job.FAILED
        job.error = str(e)
        job.save()
        _publish(r, job_id, {"status": "FAILED", "error": str(e)})
        return

    job.status = Job.DONE
    job.result_json = {**ingest_response.json(), "record_id": record_id}
    job.save()
    _publish(r, job_id, {"status": "DONE"})

        
@shared_task
def summarise_job(job_id):
    job = Job.objects.get(id=job_id)

    record_id = (job.result_json or {}).get("record_id")
    if not record_id:
        job.summary = "No extraction record found for this job."
        job.save()
        return

    try:
        response = httpx.get(
            f"{settings.PDF_EXTRACTION_SERVICE_URL}/results/{record_id}",
            timeout=30.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as e:
        job.summary = f"Could not fetch extraction: {e}"
        job.save()
        return

    extraction = response.json().get("extraction", {})

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    prompt = (
        f"You are a document analyst. Below is structured data extracted from a PDF "
        f"named '{job.filename}'. Write a concise 2—3 sentence plain-English summary "
        f"of what this document is about and its key facts. \n\n"
        f"{json.dumps(extraction, indent=2)}"
    )
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    

    job.summary = response.text
    job.save()