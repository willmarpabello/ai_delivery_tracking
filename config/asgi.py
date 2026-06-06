import os
from django.core.asgi import get_asgi_application

# 1. Set the settings profile first
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')

# 2. Initialize the standard ASGI application BEFORE importing routing or consumers
django_asgi_app = get_asgi_application()

# 3. NOW import your routing (Crucial: must happen after get_asgi_application)
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import delivery_app.routing 

# 4. Define the protocol routing map
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            delivery_app.routing.websocket_urlpatterns
        )
    ),
})