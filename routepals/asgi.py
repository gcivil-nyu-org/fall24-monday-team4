import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from locations.routing import websocket_urlpatterns as trip_websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "routepals.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                chat_websocket_urlpatterns + trip_websocket_urlpatterns
            )
        ),
    }
)
