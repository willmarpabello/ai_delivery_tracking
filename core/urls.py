from django.urls import path
from .views import register, user_login, user_logout, dashboard
from . import views

urlpatterns = [
    path('', user_login, name='login'),
    path('register/', register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('track/<int:pk>/data/', views.delivery_tracking_data, name='delivery_tracking_data'),
    path('track/<int:pk>/update/', views.delivery_tracking_update, name='delivery_tracking_update'),
    path('update-status/<int:pk>/<str:status>/', views.update_status, name='update_status'),
    path('delivery/create/', views.create_delivery, name='create_delivery'),
    path('delivery/', views.delivery_list, name='delivery_list'),
    path('delivery/update/<int:pk>/', views.update_delivery, name='update_delivery'),
    path('delivery/delete/<int:pk>/', views.delete_delivery, name='delete_delivery'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('confirm/<int:pk>/<str:action>/', views.confirm_delivery, name='confirm_delivery'),
    path('api/reports/<str:period>/', views.get_reports, name='api_reports'),
]