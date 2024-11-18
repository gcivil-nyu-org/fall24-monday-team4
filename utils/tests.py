from django.test import TestCase
from utils.s3_utils import (
    generate_presigned_url,
    upload_file_to_s3,
    delete_file_from_s3,
)
from django.core.files.uploadedfile import SimpleUploadedFile


class S3UtilsTest(TestCase):
    def setUp(self):
        self.test_file = SimpleUploadedFile(
            "test_file.txt", b"test content", content_type="text/plain"
        )
        self.test_key = None  # Will store the key after upload

    def test_upload_and_generate_url_and_delete(self):
        # Test upload
        url = upload_file_to_s3(self.test_file, "test-upload-key")
        self.assertIsNotNone(url)
        self.test_key = "test-upload-key"

        # Test generate URL
        presigned_url = generate_presigned_url(self.test_key)
        self.assertIsNotNone(presigned_url)

        # Test delete
        delete_result = delete_file_from_s3(self.test_key)
        self.assertTrue(delete_result)

        # Verify deletion
        presigned_url = generate_presigned_url(self.test_key)
        self.assertIsNone(presigned_url)

    def test_nonexistent_key(self):
        url = generate_presigned_url("nonexistent-key")
        self.assertIsNone(url)

        delete_result = delete_file_from_s3("nonexistent-key")
        self.assertFalse(delete_result)
