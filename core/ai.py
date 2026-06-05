import math
from datetime import timedelta
from django.utils import timezone


def calculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    return math.hypot(lat1 - lat2, lon1 - lon2) * 111000


def detect_anomaly(delivery, last_point=None):
    if delivery.status == "Failed":
        return "Delivery failed"

    if delivery.latitude is None or delivery.longitude is None:
        return "Missing GPS data"

    if delivery.expected_latitude is None or delivery.expected_longitude is None:
        return None

    distance_meters = calculate_distance(
        delivery.latitude,
        delivery.longitude,
        delivery.expected_latitude,
        delivery.expected_longitude
    )

    if distance_meters is None:
        return None

    if distance_meters > 1200:
        return "Rider is off the assigned route"

    if last_point and last_point.speed_kmh is not None:
        if last_point.speed_kmh <= 2:
            if timezone.now() - last_point.recorded_at > timedelta(minutes=10):
                return "Rider inactive for 10 minutes"
            return "Rider movement is too slow"
        if last_point.speed_kmh < 8:
            return "Possible traffic delay detected"

    if delivery.status == "In Transit" and distance_meters > 3500:
        if timezone.now() - delivery.created_at > timedelta(hours=1):
            return "Delivery arrival may be delayed"

    return None
