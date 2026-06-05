from django.contrib import admin
from .models import CustomUser, Delivery

admin.site.register(CustomUser)
admin.site.register(Delivery)