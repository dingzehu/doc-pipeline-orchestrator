from django.db import models

class Job(models.Model):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"
    STATUS_CHOICES = [
        (QUEUED, QUEUED),
        (PROCESSING, PROCESSING),
        (DONE, DONE),
        (FAILED, FAILED),
    ]

    filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=QUEUED   # every now Job starts in the queue
    )
    result_json = models.JSONField(null=True, blank=True)   # stores extraction result dict
    error = models.TextField(null=True, blank=True)   # stores error message if failed
    created_at = models.DateTimeField(auto_now_add=True)   # set once on insert, never updated

    def __str__(self):
        return f"{self.filename} ({self.status})"
