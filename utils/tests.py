import io
from django.test import TestCase
from moto import mock_aws
import boto3
from django.conf import settings
from utils.s3_utils import (
    upload_file_to_s3,
    generate_presigned_url,
    delete_file_from_s3,
)
import uuid


class S3UtilsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mock_aws = mock_aws()
        cls.mock_aws.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_aws.stop()
        super().tearDownClass()

    def setUp(self):
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id="fake-access-key",
            aws_secret_access_key="fake-secret-key",
        )
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.test_key = str(uuid.uuid4())

    def test_upload_file_to_s3(self):
        file = io.BytesIO(b"This is a test file")
        file.content_type = "text/plain"

        url = upload_file_to_s3(file, self.test_key)
        self.assertIsNotNone(url)

        response = self.s3.get_object(Bucket=self.bucket_name, Key=self.test_key)
        self.assertEqual(response["Body"].read(), b"This is a test file")

        head_response = self.s3.head_object(Bucket=self.bucket_name, Key=self.test_key)
        self.assertEqual(head_response["ContentType"], "text/plain")

    def test_upload_empty_file(self):
        file = io.BytesIO(b"")
        file.content_type = "text/plain"

        url = upload_file_to_s3(file, self.test_key)
        self.assertIsNotNone(url)

    def test_generate_presigned_url(self):
        self.s3.put_object(
            Bucket=self.bucket_name, Key=self.test_key, Body="dummy content"
        )

        url = generate_presigned_url(self.test_key)
        self.assertIsNotNone(url)
        self.assertIn(self.test_key, url)

    def test_generate_url_nonexistent_key(self):
        url = generate_presigned_url("nonexistent-key")
        self.assertIsNone(url)

    def test_delete_file_from_s3(self):
        self.s3.put_object(
            Bucket=self.bucket_name, Key=self.test_key, Body="dummy content"
        )

        result = delete_file_from_s3(self.test_key)
        self.assertTrue(result)

        with self.assertRaises(self.s3.exceptions.NoSuchKey):
            self.s3.get_object(Bucket=self.bucket_name, Key=self.test_key)

    def test_delete_nonexistent_file(self):
        result = delete_file_from_s3("nonexistent-key")
        self.assertFalse(result)
