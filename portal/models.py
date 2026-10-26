from django.conf import settings
from django.db import models


class MemberProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_profile')
    firebase_uid = models.CharField(max_length=128, unique=True)
    answers = models.JSONField(default=dict)
    interests = models.JSONField(default=list)
    completed = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)


class AnalysisRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='analyses')
    module_slug = models.CharField(max_length=40)
    module_title = models.CharField(max_length=120)
    label = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
