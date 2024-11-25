from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from utils.s3_utils import delete_file_from_s3
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, is_verified=instance.is_staff)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()


@receiver(pre_delete, sender=User)
def delete_user_files(sender, instance, **kwargs):
    try:
        # Delete profile photo if exists
        if instance.userprofile.photo_key:
            delete_file_from_s3(instance.userprofile.photo_key)
            instance.userprofile.delete()

        # Delete all user documents
        for doc in instance.documents.all():
            if doc.s3_key:
                delete_file_from_s3(doc.s3_key)
            doc.delete()

    except Exception as e:
        logger.error(f"Error deleting user files: {e}")
