import httpx
from django.core.files.storage import default_storage
from django.conf import settings
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from pathlib import Path

from .models import Job
from .serializers import JobSerializer
from .tasks import process_pdf


class UploadView(APIView):
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"error": "file is required"},
                status=status.HTTP_400_BAD_REQUEST
                )

        # save first to get job.id for the name below
        job = Job.objects.create(filename=uploaded_file.name)

        try:
            default_storage.save(f"{job.id}_{uploaded_file.name}", uploaded_file)
            pdf_path = str(Path(settings.MEDIA_ROOT) / f"{job.id}_{uploaded_file.name}")
            process_pdf.delay(job.id, pdf_path)
        except OSError:
            # disk/permission error — job row already exists, so records the failure
            job.status = Job.FAILED
            job.error = "Could not save uploaded file"
            job.save()
            return Response(
                JobSerializer(job).data,
                status=status.HTTP_502_BAD_GATEWAY
                )

        return Response(
            JobSerializer(job).data,
            status=status.HTTP_201_CREATED
            )


class StatusView(RetrieveAPIView):
    queryset = Job.objects.all()
    serializer_class = JobSerializer   # looks up by the "pk" URL kwarg automatically


class JobListView(ListAPIView):
    # newest jobs first, for page load
    queryset = Job.objects.all().order_by("-created_at")
    serializer_class = JobSerializer


class AskView(APIView):
    def post(self, request):
        question = request.data.get("question")
        if not question:
            return Response(
                {"error": "question is required"},
                status=status.HTTP_400_BAD_REQUEST
                )

        try:
            response = httpx.post(
                f"{settings.RAG_SEARCH_SERVICE_URL}/search",
                json={"question": question, "top_k": 5},
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError:   # network failure or non-2xx — an external boundary
            return Response(
                {"error": "rag-search-service is unavailable"},
                status=status.HTTP_502_BAD_GATEWAY
                )

        # SearchResponse dict passed straight through to the frontend
        return Response(response.json())
