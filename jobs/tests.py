from django.core.files.uploadedfile import SimpleUploadedFile

from rest_framework.test import APITestCase
from rest_framework import status

from django.urls import reverse

from .models import Job

from unittest.mock import patch


class UploadViewTests(APITestCase):
    def test_success_upload(self):
        self.fake_file = SimpleUploadedFile(
            name="test.pdf",
            content=b"\x47\x49\x46\x38\x39\x61",  # dummy bytes
        )
        self.res_upload = self.client.post(
            reverse('upload'),
            {'file': self.fake_file},
            format='multipart')

        job = Job.objects.get(filename="test.pdf")

        assert self.res_upload.status_code == status.HTTP_201_CREATED
        assert self.res_upload.data['filename'] == 'test.pdf'
        assert self.res_upload.data['status'] == Job.QUEUED
        assert job.status == Job.QUEUED

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


class StatusViewTest(APITestCase):
    def test_success_fetch(self):
        