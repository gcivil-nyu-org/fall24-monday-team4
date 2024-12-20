# Create utils/security.py
import json
from django.utils.html import escape


class XSSMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only process JSON responses
        if (
            hasattr(response, "content_type")
            and "application/json" in response.content_type
        ):
            content = response.content.decode()
            if content:
                try:
                    content = response.content.decode()
                    data = json.loads(content)
                    # Rest of the middleware code...
                except json.JSONDecodeError:
                    return response  # Return original response if JSON is invalid

                # Recursively escape all string values
                def escape_json(obj):
                    if isinstance(obj, str):
                        return escape(obj)
                    elif isinstance(obj, dict):
                        return {k: escape_json(v) for k, v in obj.items()}
                    elif isinstance(obj, (list, tuple)):
                        return [escape_json(item) for item in obj]
                    return obj

                escaped_data = escape_json(data)
                response.content = json.dumps(escaped_data).encode()

        return response
