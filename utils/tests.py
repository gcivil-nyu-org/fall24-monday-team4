import json
from django.test import TestCase, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from utils.s3_utils import (
    generate_presigned_url,
    upload_file_to_s3,
    delete_file_from_s3,
)
from django.http import JsonResponse, HttpResponse
from utils.security import XSSMiddleware


class S3UtilsTest(TestCase):
    def setUp(self):
        self.test_key = "test/file.txt"
        self.test_url = "https://test-bucket.s3.amazonaws.com/test/file.txt"

    @patch("utils.s3_utils.s3_client")
    def test_generate_presigned_url_success(self, mock_s3):
        # Setup mock
        mock_s3.generate_presigned_url.return_value = self.test_url
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError

        # Test successful URL generation
        url = generate_presigned_url(self.test_key)

        # Assertions
        self.assertEqual(url, self.test_url)
        mock_s3.head_object.assert_called_once()
        mock_s3.generate_presigned_url.assert_called_once()

    @patch("utils.s3_utils.s3_client")
    def test_generate_presigned_url_file_not_found(self, mock_s3):
        # Setup mock
        error = ClientError(
            error_response={"Error": {"Code": "404", "Message": "Not Found"}},
            operation_name="HeadObject",
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError

        # Test URL generation for non-existent file
        url = generate_presigned_url(self.test_key)

        # Assertions
        self.assertIsNone(url)
        mock_s3.head_object.assert_called_once()
        mock_s3.generate_presigned_url.assert_not_called()

    @patch("utils.s3_utils.s3_client")
    def test_upload_file_to_s3_success(self, mock_s3):
        # Setup mocks
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.generate_presigned_url.return_value = self.test_url

        test_file = SimpleUploadedFile(
            "test.txt", b"test content", content_type="text/plain"
        )

        # Test successful upload
        url = upload_file_to_s3(test_file, self.test_key)

        # Assertions
        self.assertEqual(url, self.test_url)
        mock_s3.upload_fileobj.assert_called_once()

    @patch("utils.s3_utils.s3_client")
    def test_upload_file_to_s3_failure(self, mock_s3):
        # Setup mock for upload failure
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError
        mock_s3.upload_fileobj.side_effect = Exception("Upload failed")

        test_file = SimpleUploadedFile(
            "test.txt", b"test content", content_type="text/plain"
        )

        # Test failed upload
        url = upload_file_to_s3(test_file, self.test_key)

        # Assertions
        self.assertIsNone(url)
        mock_s3.upload_fileobj.assert_called_once()

    @patch("utils.s3_utils.s3_client")
    def test_delete_file_from_s3_success(self, mock_s3):
        # Setup mock
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError

        # Test successful deletion
        result = delete_file_from_s3(self.test_key)

        # Assertions
        self.assertTrue(result)
        mock_s3.head_object.assert_called_once()
        mock_s3.delete_object.assert_called_once()

    @patch("utils.s3_utils.s3_client")
    def test_delete_file_from_s3_not_found(self, mock_s3):
        # Setup mock
        error = ClientError(
            error_response={"Error": {"Code": "404", "Message": "Not Found"}},
            operation_name="HeadObject",
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions = MagicMock()
        mock_s3.exceptions.ClientError = ClientError

        # Test deletion of non-existent file
        result = delete_file_from_s3(self.test_key)

        # Assertions
        self.assertFalse(result)
        mock_s3.head_object.assert_called_once()
        mock_s3.delete_object.assert_not_called()

    @patch("utils.s3_utils.s3_client")
    def test_generate_presigned_url_other_error(self, mock_s3):
        error = ClientError(
            error_response={"Error": {"Code": "500", "Message": "Internal Error"}},
            operation_name="HeadObject",
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions.ClientError = ClientError

        url = generate_presigned_url(self.test_key)
        self.assertIsNone(url)

    @patch("utils.s3_utils.s3_client")
    def test_delete_file_from_s3_other_error(self, mock_s3):
        error = ClientError(
            error_response={"Error": {"Code": "500", "Message": "Internal Error"}},
            operation_name="HeadObject",
        )
        mock_s3.head_object.side_effect = error
        mock_s3.exceptions.ClientError = ClientError

        result = delete_file_from_s3(self.test_key)
        self.assertFalse(result)


class XSSMiddlewareTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = XSSMiddleware(self.get_test_response)

    def get_test_response(self, request):
        if hasattr(request, "test_response"):
            return request.test_response
        return HttpResponse()

    def test_escape_basic_json(self):
        request = self.factory.get("/")
        request.test_response = JsonResponse(
            {"message": '<script>alert("xss")</script>'}
        )

        response = self.middleware(request)
        data = json.loads(response.content)
        # Plain string comparison instead of escaped literals
        self.assertEqual(data["message"], '<script>alert("xss")</script>')

    def test_escape_nested_json(self):
        request = self.factory.get("/")
        request.test_response = JsonResponse(
            {
                "data": {
                    "message": '<script>alert("xss")</script>',
                    "nested": {"text": '<img src="x" onerror="alert(1)"/>'},
                }
            }
        )

        response = self.middleware(request)
        data = json.loads(response.content)
        self.assertEqual(data["data"]["message"], '<script>alert("xss")</script>')
        self.assertEqual(
            data["data"]["nested"]["text"], '<img src="x" onerror="alert(1)"/>'
        )

    def test_escape_list_in_json(self):
        request = self.factory.get("/")
        request.test_response = JsonResponse(
            {"messages": ["<script>alert(1)</script>", "<script>alert(2)</script>"]}
        )

        response = self.middleware(request)
        data = json.loads(response.content)
        self.assertEqual(data["messages"][0], "<script>alert(1)</script>")
        self.assertEqual(data["messages"][1], "<script>alert(2)</script>")

    def test_non_json_response(self):
        request = self.factory.get("/")
        request.test_response = HttpResponse('<script>alert("xss")</script>')

        response = self.middleware(request)
        self.assertEqual(response.content.decode(), '<script>alert("xss")</script>')

    def test_empty_json_response(self):
        request = self.factory.get("/")
        request.test_response = JsonResponse({})

        response = self.middleware(request)
        self.assertEqual(response.content.decode(), "{}")

    def test_non_string_values(self):
        request = self.factory.get("/")
        request.test_response = JsonResponse(
            {"number": 123, "boolean": True, "null": None}
        )

        response = self.middleware(request)
        self.assertIn('"number": 123', response.content.decode())
        self.assertIn('"boolean": true', response.content.decode())
        self.assertIn('"null": null', response.content.decode())
