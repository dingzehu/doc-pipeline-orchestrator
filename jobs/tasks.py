import json

import httpx
import redis
from celery import shared_task
from django.conf import settings

from .models import Job


def _publish(r, job_id, payload):
    r.publish(f"job:{job_id}", json.dumps(payload))


@shared_task
def process_pdf(job_id, pdf_path):
    job = Job.objects.get(id=job_id)
    job.status = Job.PROCESSING
    job.save()

    r = redis.from_url(settings.CELERY_BROKER_URL)
    _publish(r, job_id, {"status": "PROCESSING", "step": "started"})

    try:
        with open(pdf_path, "rb") as f:
            extraction_response = httpx.post(
                f"{settings.PDF_EXTRACTION_SERVICE_URL}/extract",
                files={"file": f},
                timeout=60.0,
            )
        extraction_response.raise_for_status()
        _publish(r, job_id, {"status": "PROCESSING", "step": "extracted"})

        with open(pdf_path, "rb") as f:
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
    job.result_json = ingest_response.json()
    job.save()
    _publish(r, job_id, {"status": "DONE"})

        