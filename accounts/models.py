from django.db import models
from django.contrib.auth.models import User


class Status(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "status"


class UserDocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    s3_key = models.CharField(max_length=255, unique=True, null=False)
    filename = models.CharField(max_length=255, null=False)
    file_type = models.CharField(max_length=50, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    status = models.ForeignKey(
        Status, on_delete=models.PROTECT, default=1, related_name="documents"
    )
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.filename} - {self.user.username}"

    class Meta:
        db_table = "user_documents"

class UserReports(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made', null=False)
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received', null=False)
    subject = models.CharField(max_length=255, null=False)
    description = models.TextField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    is_acknowledged = models.BooleanField(default=False)

    def __str__(self):
        return f"Report by {self.reporter.username} on {self.reported_user.username}"

    class Meta:
        db_table = "user_reports"

