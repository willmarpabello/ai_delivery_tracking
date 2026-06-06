import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import delivery_app.routing # Import your new routing file

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            delivery_app.routing.websocket_urlpatterns
        )
    ),
})