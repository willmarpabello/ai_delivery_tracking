import os
from django.core.asgi import get_asgi_application

# 1. Set the settings profile first (pointing to your config folder)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 2. Initialize the standard ASGI application BEFORE importing routing or consumers
django_asgi_app = get_asgi_application()

# 3. NOW import your routing from your 'core' app folder
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import core.routing  # Looking inside your core folder

# 4. Define the protocol routing map
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            core.routing.websocket_urlpatterns  # Looking inside your core folder
        )
    ),
})