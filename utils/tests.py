import io
from django.test import TestCase, override_settings
from moto import mock_aws
import boto3
from utils.s3_utils import (
    upload_file_to_s3,
    generate_presigned_url,
    delete_file_from_s3,
)
import uuid
from botocore.exceptions import ClientError

TEST_BUCKET_NAME = 'test-bucket'

@override_settings(
    AWS_STORAGE_BUCKET_NAME=TEST_BUCKET_NAME,
    AWS_ACCESS_KEY_ID='fake-access-key',
    AWS_SECRET_ACCESS_KEY='fake-secret-key'
)
@mock_aws
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
        self.bucket_name = TEST_BUCKET_NAME  # Use test bucket name instead of settings
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id="fake-access-key",
            aws_secret_access_key="fake-secret-key",
        )
        self.s3.create_bucket(Bucket=self.bucket_name)
        self.test_key = str(uuid.uuid4())
        self.test_content = b"This is a test file"
        self.test_content_type = "text/plain"

    def create_test_file(self, content=None, content_type=None):
        """Helper method to create test file"""
        file = io.BytesIO(content or self.test_content)
        file.content_type = content_type or self.test_content_type
        return file

    def test_upload_file_to_s3_success(self):
        """Test successful file upload to S3"""
        file = self.create_test_file()
        url = upload_file_to_s3(file, self.test_key)

        self.assertIsNotNone(url)

        # Verify file content
        response = self.s3.get_object(Bucket=self.bucket_name, Key=self.test_key)
        self.assertEqual(response["Body"].read(), self.test_content)

        # Verify content type
        head_response = self.s3.head_object(Bucket=self.bucket_name, Key=self.test_key)
        self.assertEqual(head_response["ContentType"], self.test_content_type)

    def test_upload_empty_file(self):
        """Test uploading an empty file"""
        file = self.create_test_file(content=b"")
        url = upload_file_to_s3(file, self.test_key)
        self.assertIsNotNone(url)

    def test_upload_file_invalid_inputs(self):
        """Test upload with invalid inputs"""
        # Test with None file
        self.assertIsNone(upload_file_to_s3(None, self.test_key))

        # Test with None key
        file = self.create_test_file()
        self.assertIsNone(upload_file_to_s3(file, None))

        # Test with empty key
        self.assertIsNone(upload_file_to_s3(file, ""))

    @override_settings(AWS_STORAGE_BUCKET_NAME='nonexistent-bucket')
    def test_upload_file_nonexistent_bucket(self):
        """Test upload to nonexistent bucket"""
        file = self.create_test_file()
        url = upload_file_to_s3(file, self.test_key)
        self.assertIsNone(url)

    def test_generate_presigned_url_success(self):
        """Test successful presigned URL generation"""
        # Upload test file first
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.test_key,
            Body=self.test_content
        )

        url = generate_presigned_url(self.test_key)
        self.assertIsNotNone(url)
        self.assertIn(self.test_key, url)

    def test_generate_presigned_url_invalid_inputs(self):
        """Test presigned URL generation with invalid inputs"""
        self.assertIsNone(generate_presigned_url(None))
        self.assertIsNone(generate_presigned_url(""))

    def test_generate_url_nonexistent_key(self):
        """Test presigned URL generation for nonexistent file"""
        url = generate_presigned_url("nonexistent-key")
        self.assertIsNone(url)

    def test_delete_file_success(self):
        """Test successful file deletion"""
        # Upload test file first
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=self.test_key,
            Body=self.test_content
        )

        result = delete_file_from_s3(self.test_key)
        self.assertTrue(result)

        # Verify file is deleted
        with self.assertRaises(ClientError) as context:
            self.s3.head_object(Bucket=self.bucket_name, Key=self.test_key)
        self.assertEqual(
            context.exception.response['Error']['Code'],
            '404'
        )

    def test_delete_file_invalid_inputs(self):
        """Test file deletion with invalid inputs"""
        self.assertFalse(delete_file_from_s3(None))
        self.assertFalse(delete_file_from_s3(""))

    def test_delete_nonexistent_file(self):
        """Test deleting a nonexistent file"""
        result = delete_file_from_s3("nonexistent-key")
        self.assertFalse(result)

    @override_settings(AWS_STORAGE_BUCKET_NAME='nonexistent-bucket')
    def test_delete_file_nonexistent_bucket(self):
        """Test deletion from nonexistent bucket"""
        result = delete_file_from_s3(self.test_key)
        self.assertFalse(result)

    def tearDown(self):
        """Clean up any test files"""
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=self.test_key)
        except:
            pass  # Ignore any errors during cleanup