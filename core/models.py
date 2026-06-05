from django.contrib.auth.models import AbstractUser
from django.db import models


# CUSTOM USER
class CustomUser(AbstractUser):

    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('rider', 'Rider'),
        ('customer', 'Customer'),
    )

    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )

    address = models.TextField(blank=True, null=True)

    contact_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    profile_picture = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True
    )


# DELIVERY MODEL
class Delivery(models.Model):

    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Transit', 'In Transit'),
        ('Delivered', 'Delivered'),
        ('Failed', 'Failed'),
        ('Waiting Confirmation', 'Waiting Confirmation'),
    ]

    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='customer_deliveries'
    )

    rider = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rider_deliveries'
    )

    address = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    confirmation_status = models.CharField(
        max_length=30,
        default='Pending'
    )
 
    # GPS TRACKING
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    expected_latitude = models.FloatField(null=True, blank=True)
    expected_longitude = models.FloatField(null=True, blank=True)

    # ALERTS
    alert_triggered = models.BooleanField(default=False)

    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    customer_confirmed = models.BooleanField(default=False)
    rider_requested_confirmation = models.BooleanField(default=False)

    # DELIVERY PROOF
    proof_image = models.ImageField(
        upload_to='proof/',
        null=True,
        blank=True
    )

    signature = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Delivery #{self.id}"


class DeliveryTrackingPoint(models.Model):
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name='tracking_points'
    )

    latitude = models.FloatField()
    longitude = models.FloatField()
    speed_kmh = models.FloatField(null=True, blank=True)
    distance_to_destination = models.FloatField(null=True, blank=True)
    eta_minutes = models.IntegerField(null=True, blank=True)
    route_deviation = models.BooleanField(default=False)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Delivery #{self.delivery.id} @ {self.recorded_at.strftime('%Y-%m-%d %H:%M:%S')}"


# AI LOGS
class DeliveryLog(models.Model):

    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE
    )

    action = models.CharField(max_length=100)

    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    anomaly_detected = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.delivery.id} - {self.action}"