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

    def test_response_without_content_type(self):
        """Test handling response without content_type attribute"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        delattr(mock_response, "content_type")  # Force hasattr to return False
        request.test_response = mock_response

        response = self.middleware(request)
        self.assertEqual(response, mock_response)

    def test_non_json_content_type(self):
        """Test handling non-JSON content type"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "text/html"
        request.test_response = mock_response

        response = self.middleware(request)
        self.assertEqual(response, mock_response)

    def test_empty_json_content(self):
        """Test handling empty content in JSON response"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "application/json"
        mock_response.content = b""
        request.test_response = mock_response

        response = self.middleware(request)
        self.assertEqual(response, mock_response)

    def test_invalid_json_decode(self):
        """Test handling invalid JSON content"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "application/json"

        # Make content itself a MagicMock
        mock_content = MagicMock()
        mock_content.decode.return_value = "invalid json"
        mock_response.content = mock_content

        request.test_response = mock_response
        response = self.middleware(request)
        self.assertEqual(response, mock_response)

    def test_tuple_in_json(self):
        """Test handling tuple in JSON content"""
        request = self.factory.get("/")
        request.test_response = JsonResponse(
            {"tuple": tuple(["<script>alert(1)</script>", "<script>alert(2)</script>"])}
        )

        response = self.middleware(request)
        data = json.loads(response.content)
        self.assertEqual(data["tuple"][0], "<script>alert(1)</script>")
        self.assertEqual(data["tuple"][1], "<script>alert(2)</script>")

    def test_escape_string_xss(self):
        """Test escaping string containing potential XSS"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "application/json"

        # Create mock content with a string containing XSS
        xss_string = '{"message": "<script>alert(\'xss\')</script>"}'
        mock_content = MagicMock()
        mock_content.decode.return_value = xss_string
        mock_response.content = mock_content

        request.test_response = mock_response
        response = self.middleware(request)
        content = json.loads(response.content.decode())
        self.assertEqual(
            content["message"], "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        )

    def test_escape_nested_dict_xss(self):
        """Test escaping nested dictionary containing XSS"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "application/json"

        nested_xss = '{"user": {"name": "<script>alert(\'xss\')</script>"}}'
        mock_content = MagicMock()
        mock_content.decode.return_value = nested_xss
        mock_response.content = mock_content

        request.test_response = mock_response
        response = self.middleware(request)
        content = json.loads(response.content.decode())
        self.assertEqual(
            content["user"]["name"],
            "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;",
        )

    def test_escape_list_xss(self):
        """Test escaping list containing XSS"""
        request = self.factory.get("/")
        mock_response = MagicMock()
        mock_response.content_type = "application/json"

        list_xss = '{"messages": ["<script>alert(1)</script>", "<img onerror=alert(1) src=x>"]}'
        mock_content = MagicMock()
        mock_content.decode.return_value = list_xss
        mock_response.content = mock_content

        request.test_response = mock_response
        response = self.middleware(request)
        content = json.loads(response.content.decode())
        self.assertEqual(
            content["messages"][0], "&lt;script&gt;alert(1)&lt;/script&gt;"
        )
        self.assertEqual(content["messages"][1], "&lt;img onerror=alert(1) src=x&gt;")

    def test_escape_json_number_value(self):
        # Create a mock get_response function that returns our mock response
        mock_response = MagicMock()
        mock_response.content_type = "application/json"
        mock_response.content = json.dumps({"number": 42}).encode()

        def mock_get_response(request):
            return mock_response

        middleware = XSSMiddleware(mock_get_response)

        # Process the response through middleware
        processed_response = middleware.__call__(
            None
        )  # None as request since we don't use it
        processed_content = json.loads(processed_response.content.decode())

        # The number should remain unchanged since it's not a string
        self.assertEqual(processed_content["number"], 42)
