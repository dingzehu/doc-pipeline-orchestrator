from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ["id", "filename", "status", "result_json", "error", "created_at"]
        read_only_fields = ["id", "status", "result_json", "error", "created_at"]