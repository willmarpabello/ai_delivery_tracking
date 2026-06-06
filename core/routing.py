from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Matches the URL you set in your JavaScript
    re_path(r'ws/live-monitoring/$', consumers.LiveMonitoringConsumer.as_asgi()),
    
    # Keep your existing delivery updates route here as well
    # re_path(r'ws/delivery-updates/$', consumers.DeliveryUpdatesConsumer.as_asgi()), 
]