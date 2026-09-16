import os
import tempfile
from datetime import timedelta
from unittest.mock import MagicMock, patch

import httpx
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Job
from .tasks import process_pdf


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UploadViewTests(APITestCase):
    def test_success_upload(self):
        self.fake_file = SimpleUploadedFile(
            name="test.pdf",
            content=b"\x47\x49\x46\x38\x39\x61",  # dummy bytes
        )
        with patch("jobs.views.process_pdf.delay") as mock_delay:
            self.res_upload = self.client.post(
                reverse('upload'),
                {'file': self.fake_file},
                format='multipart')

        job = Job.objects.get(filename="test.pdf")

        assert self.res_upload.status_code == status.HTTP_201_CREATED
        assert self.res_upload.data['filename'] == 'test.pdf'
        assert self.res_upload.data['status'] == Job.QUEUED
        assert job.status == Job.QUEUED
        assert mock_delay.call_count == 1

    def test_missing_upload(self):
        self.res_upload = self.client.post(
            reverse('upload'),
        )

        assert self.res_upload.status_code == status.HTTP_400_BAD_REQUEST
        assert Job.objects.count() == 0

    def test_upload_storage_failure(self):
        with patch("jobs.views.default_storage.save") as jobs_save:
            jobs_save.side_effect = OSError
            self.fake_file = SimpleUploadedFile(
                name="test.pdf",
                content=b"\x47\x49\x46\x38\x39\x61",  # dummy bytes
            )
            self.res_upload = self.client.post(
                reverse('upload'),
                {'file': self.fake_file},
                format='multipart')

            job = Job.objects.get(filename="test.pdf")

            assert self.res_upload.status_code == status.HTTP_502_BAD_GATEWAY
            assert job.status == Job.FAILED
            assert job.error == "Could not save uploaded file"
            assert self.res_upload.data['filename'] == 'test.pdf'
            assert self.res_upload.data['status'] == Job.FAILED


class StatusViewTests(APITestCase):
    def test_success_fetch(self):
        job = Job.objects.create(filename="test.pdf")

        self.response = self.client.get(reverse('status', kwargs={'pk': job.id}))

        assert self.response.status_code == status.HTTP_200_OK
        assert self.response.data['id'] == job.id
        assert self.response.data['filename'] == 'test.pdf'
        assert self.response.data['status'] == Job.QUEUED

    def test_non_exist_id(self):
        self.response = self.client.get(reverse('status', kwargs={'pk': 9999999}))

        assert self.response.status_code == status.HTTP_404_NOT_FOUND


class JobListViewTests(APITestCase):
    def test_ordered_existed_job_list(self):
        job_0 = Job.objects.create(filename='test_0.pdf')
        Job.objects.filter(pk=job_0.id).update(
            created_at=timezone.now() - timedelta(minutes=10))
        job_1 = Job.objects.create(filename='test_1.pdf')
        Job.objects.filter(pk=job_1.id).update(
            created_at=timezone.now() - timedelta(minutes=5))
        job_2 = Job.objects.create(filename='test_2.pdf')
        Job.objects.filter(pk=job_2.id).update(
            created_at=timezone.now() - timedelta(minutes=1))

        self.response = self.client.get(reverse('job-list'))

        assert self.response.status_code == status.HTTP_200_OK
        assert self.response.data[0]['id'] == job_2.id
        assert self.response.data[-1]['id'] == job_0.id
        assert len(self.response.data) == 3


class AskViewTests(APITestCase):
    def test_missing_question(self):
        self.response = self.client.post(
            reverse('ask'),
        )

        assert self.response.status_code == status.HTTP_400_BAD_REQUEST

    def test_success_ask(self):
        with patch('jobs.views.httpx.post') as mock_post:
            mock_post.return_value.json.return_value = {
                "answer": "some answer", "sources": []}

            self.response = self.client.post(
                reverse('ask'), {"question": "what is ..."}, format='json')

            assert self.response.status_code == status.HTTP_200_OK
            assert self.response.data == {"answer": "some answer", "sources": []}

    def test_upstream_fail(self):
        with patch('jobs.views.httpx.post') as mock_post:
            mock_post.side_effect = httpx.HTTPError("upstream error")

            self.response = self.client.post(
                reverse('ask'), {"question": "what is ..."}, format='json')

            assert self.response.status_code == status.HTTP_502_BAD_GATEWAY


class ProcessPdfTaskTests(TestCase):
    def setUp(self):
        self.job = Job.objects.create(filename="test.pdf")
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(b"%PDF-1.4 fake content")
        tmp.close()
        self.pdf_path = tmp.name
        redis_patcher = patch("jobs.tasks.redis.from_url")
        redis_patcher.start()
        self.addCleanup(redis_patcher.stop)

    def tearDown(self):
        os.unlink(self.pdf_path)

    def test_success(self):
        extraction_mock = MagicMock()
        extraction_mock.json.return_value = {"record_id": 42}

        ingest_mock = MagicMock()
        ingest_mock.json.return_value = {"status": "indexed"}

        with patch("jobs.tasks.httpx.post") as mock_post:
            mock_post.side_effect = [extraction_mock, ingest_mock]
            process_pdf(self.job.id, self.pdf_path)

        self.job.refresh_from_db()
        assert self.job.status == Job.DONE
        assert self.job.result_json == {"status": "indexed"}

    def test_extraction_fails(self):
        with patch("jobs.tasks.httpx.post") as mock_post:
            mock_post.side_effect = httpx.HTTPError("extraction error")
            process_pdf(self.job.id, self.pdf_path)

        self.job.refresh_from_db()
        assert self.job.status == Job.FAILED
        assert self.job.error == "extraction error"

    def test_ingestion_fails(self):
        extraction_mock = MagicMock()
        extraction_mock.json.return_value = {"record_id": 42}

        with patch("jobs.tasks.httpx.post") as mock_post:
            mock_post.side_effect = [extraction_mock, httpx.HTTPError("ingest error")]
            process_pdf(self.job.id, self.pdf_path)

        self.job.refresh_from_db()
        assert self.job.status == Job.FAILED
        assert self.job.error == "ingest error"
            
