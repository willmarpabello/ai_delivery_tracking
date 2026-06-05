from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.http import JsonResponse
from django.utils import timezone
from .models import CustomUser, Delivery, DeliveryLog, DeliveryTrackingPoint
from .ai import detect_anomaly, calculate_distance
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.db.models import Max, OuterRef
from datetime import timedelta

def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST.get('email')
        password = request.POST['password']
        user_type = request.POST['user_type']

# prevent duplicate users
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type
        )
        login(request, user)  # auto login
        return redirect('dashboard')

    return render(request, 'register.html')
    
def update_delivery(request, delivery_id):
    delivery = Delivery.objects.get(id=delivery_id)

    delivery.status = "Delivered"
    delivery.save()

    alert = detect_anomaly(delivery)

    if alert:
        print("ALERT:", alert)  # later: send notification

    return redirect('dashboard')    


def user_login(request):
    error = None

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            error = "Invalid username or password"

    return render(request, "login.html", {"error": error})

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    user = request.user

    # SAFETY CHECK
    if user.user_type is None:
        return render(request, 'login.html')

    # ADMIN DASHBOARD
    if user.user_type == 'admin':

        customers = CustomUser.objects.filter(user_type='customer')
        riders = CustomUser.objects.filter(user_type='rider')

        total_deliveries = Delivery.objects.count()
        recent_deliveries = Delivery.objects.order_by('-created_at')[:5]

        # STATUS BREAKDOWN
        pending_count = Delivery.objects.filter(status='Pending').count()
        delivered_count = Delivery.objects.filter(status='Delivered').count()
        transit_count = Delivery.objects.filter(status='In Transit').count()
        failed_count = Delivery.objects.filter(status='Failed').count()
        waiting_confirm = Delivery.objects.filter(status="Waiting Confirmation").count()

        # ✅ LIVE TRACKING FIX (IMPORTANT PART)
        latest_logs = DeliveryLog.objects.filter(
            delivery__status="In Transit"
        ).order_by('-timestamp')

        context = {
            # TABLE DATA
            'customers': customers,
            'riders': riders,
            'recent_deliveries': recent_deliveries,
            'latest_logs': latest_logs,

            # STATS
            'deliveries': total_deliveries,
            'pending_count': pending_count,
            'delivered_count': delivered_count,
            'transit_count': transit_count,
            'failed_count': failed_count,
            'waiting_confirm': waiting_confirm,
        }

        return render(request, 'admin_dashboard.html', context)
   
    elif user.user_type == 'rider':
        rider_deliveries = Delivery.objects.filter(rider=user)
        delivery_count = rider_deliveries.count()

        context = {
            'deliveries': rider_deliveries,
            'delivery_count': delivery_count,
            'in_transit_count': rider_deliveries.filter(status='In Transit').count(),
            'delivered_count': rider_deliveries.filter(status='Delivered').count(),
            'pending_count': rider_deliveries.filter(status='Pending').count(),
        }

        return render(request, 'rider_dashboard.html', context)

    # 🛒 CUSTOMER DASHBOARD
    elif user.user_type == 'customer':
        deliveries = Delivery.objects.filter(customer=request.user).order_by('-created_at')
        recent_deliveries = deliveries[:5]
        customers = CustomUser.objects.filter(user_type='customer')
        riders = CustomUser.objects.filter(user_type='rider')
        failed_count = deliveries.filter(status='Failed').count()

        live_delivery = deliveries.filter(status='In Transit').first()

        context = {
            'deliveries': deliveries,
            'delivery_count': deliveries.count(),
            'recent_deliveries': recent_deliveries,
            'delivered_count': deliveries.filter(status='Delivered').count(),
            'transit_count': deliveries.filter(status='In Transit').count(),
            'pending_count': deliveries.filter(status='Pending').count(),
            'failed_count': failed_count,
            'customers': customers,
            'riders': riders,
            'live_delivery': live_delivery,
        }

        return render(request, 'customer_dashboard.html', context)

@login_required
def delivery_tracking_data(request, pk):
    delivery = get_object_or_404(Delivery, id=pk)

    if request.user != delivery.customer and request.user != delivery.rider and request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    history = [
        {
            'latitude': point.latitude,
            'longitude': point.longitude,
            'speed_kmh': point.speed_kmh,
            'distance_to_destination': point.distance_to_destination,
            'eta_minutes': point.eta_minutes,
            'route_deviation': point.route_deviation,
            'recorded_at': point.recorded_at.isoformat(),
        }
        for point in delivery.tracking_points.order_by('recorded_at')
    ]

    last_point = delivery.tracking_points.order_by('-recorded_at').first()
    alert = detect_anomaly(delivery, last_point=last_point)

    return JsonResponse({
        'success': True,
        'delivery_id': delivery.id,
        'status': delivery.status,
        'latitude': delivery.latitude,
        'longitude': delivery.longitude,
        'destination_latitude': delivery.expected_latitude,
        'destination_longitude': delivery.expected_longitude,
        'eta_minutes': last_point.eta_minutes if last_point else None,
        'distance_to_destination': last_point.distance_to_destination if last_point else None,
        'speed_kmh': last_point.speed_kmh if last_point else None,
        'alert': alert,
        'route_deviation': last_point.route_deviation if last_point else False,
        'history': history,
    })

@login_required
def delivery_tracking_update(request, pk):
    delivery = get_object_or_404(Delivery, id=pk)

    if request.user != delivery.rider and request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Forbidden'}, status=403)

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    speed = request.GET.get('speed')

    if not lat or not lng:
        return JsonResponse({'success': False, 'error': 'Missing GPS coordinates'})

    try:
        lat = float(lat)
        lng = float(lng)
        speed_kmh = float(speed) if speed else 0.0
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid GPS values'})

    delivery.latitude = lat
    delivery.longitude = lng
    if delivery.status == 'Pending':
        delivery.status = 'In Transit'

    distance_to_destination = None
    eta_minutes = None
    route_deviation = False

    if delivery.expected_latitude is not None and delivery.expected_longitude is not None:
        distance_to_destination = calculate_distance(
            lat, lng,
            delivery.expected_latitude,
            delivery.expected_longitude
        )
        if speed_kmh > 0:
            eta_minutes = int(round(distance_to_destination / 1000 / speed_kmh * 60))

        route_deviation = distance_to_destination > 1200

    delivery.save()

    last_point = delivery.tracking_points.order_by('-recorded_at').first()
    DeliveryTrackingPoint.objects.create(
        delivery=delivery,
        latitude=lat,
        longitude=lng,
        speed_kmh=speed_kmh,
        distance_to_destination=distance_to_destination,
        eta_minutes=eta_minutes,
        route_deviation=route_deviation,
    )

    alert = detect_anomaly(delivery, last_point=last_point)

    if alert:
        delivery.alert_triggered = True
        delivery.save()
        DeliveryLog.objects.create(
            delivery=delivery,
            action='Alert: ' + alert,
            latitude=lat,
            longitude=lng,
            anomaly_detected=True,
        )

    return JsonResponse({
        'success': True,
        'delivery_id': delivery.id,
        'status': delivery.status,
        'alert': alert,
        'eta_minutes': eta_minutes,
        'distance_to_destination': distance_to_destination,
        'route_deviation': route_deviation,
    })

@login_required
def update_status(request, pk, status):

    delivery = get_object_or_404(Delivery, id=pk)

    # SIMULATED GPS
    delivery.latitude = 14.50
    delivery.longitude = 121.00

    delivery.status = status
    delivery.save()

     # 🚨 AI CHECK (PUT TRY/EXCEPT HERE)
    try:
        alert = detect_anomaly(delivery)
    except Exception:
        alert = None

    # 🚚 IF RIDER MARKS DELIVERED → WAITING CONFIRMATION
    if status == "Delivered":
        delivery.status = "Waiting Confirmation"
        delivery.rider_requested_confirmation = True
        delivery.save()

    # 📌 CREATE LOG
    DeliveryLog.objects.create(
        delivery=delivery,
        action=status,
        latitude=delivery.latitude,
        longitude=delivery.longitude,
        anomaly_detected=True if alert else False
    )

    # 🚨 ALERT HANDLING
    if alert:
        delivery.alert_triggered = True
        delivery.save()
        print("🚨 ALERT:", alert)

    return redirect('dashboard')

@login_required
def create_delivery(request):

    if request.user.user_type != 'admin':
        return redirect('dashboard')

    customers = CustomUser.objects.filter(user_type='customer')
    riders = CustomUser.objects.filter(user_type='rider')

    if request.method == "POST":
        customer_id = request.POST['customer']
        rider_id = request.POST['rider']
        location = request.POST['location']

        Delivery.objects.create(
            customer_id=customer_id,
            rider_id=rider_id,
            address=location,
            status="Pending"
        )

        return redirect('delivery_list')

    return render(request, 'create_delivery.html', {
        'customers': customers,
        'riders': riders
    })

@login_required
def delivery_list(request):

    if request.user.user_type != 'admin':
        return redirect('dashboard')

    deliveries = Delivery.objects.all().order_by('-created_at')

    return render(request, 'delivery_list.html', {
        'deliveries': deliveries
    })

@login_required
def update_delivery(request, pk):

    delivery = get_object_or_404(Delivery, id=pk)

    customers = CustomUser.objects.filter(user_type='customer')
    riders = CustomUser.objects.filter(user_type='rider')

    if request.method == "POST":
        delivery.customer_id = request.POST['customer']
        delivery.rider_id = request.POST['rider']
        delivery.location = request.POST['location']
        delivery.status = request.POST['status']
        delivery.save()

        return redirect('delivery_list')

    return render(request, 'update_delivery.html', {
        'delivery': delivery,
        'customers': customers,
        'riders': riders
    })

@login_required
def delete_delivery(request, pk):

    if request.user.user_type != 'admin':
        return redirect('dashboard')

    delivery = get_object_or_404(Delivery, id=pk)
    delivery.delete()

    return redirect('delivery_list')

@login_required
def update_profile(request):

    user = request.user

    if request.method == "POST":

        user.email = request.POST.get('email')
        user.address = request.POST.get('address')
        user.contact_number = request.POST.get('contact_number')

        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']

        user.save()

        return redirect('dashboard')

    return render(request, 'customer_dashboard.html')

def confirm_delivery(request, pk, action):
    delivery = get_object_or_404(Delivery, id=pk)

    if action == "received":
        delivery.status = "Delivered"
        delivery.customer_confirmed = True

    elif action == "not_received":
        delivery.status = "Failed"
        delivery.customer_confirmed = False

    delivery.save()

    return redirect('dashboard')

def get_active_tracking(request):
    logs = DeliveryLog.objects.filter(
        delivery__status="In Transit"
    ).order_by("-timestamp")

    return render(request, "dashboard.html", {
        "tracking_logs": logs
    })

def get_reports(request, period):
    now = timezone.now()
    if period == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0)
    elif period == 'weekly':
        start_date = now - timedelta(days=7)
    else: # monthly
        start_date = now - timedelta(days=30)

    deliveries = Delivery.objects.filter(created_at__gte=start_date).order_by('-created_at')
    
    data = [{
        'id': d.id,
        'customer': d.customer.username,
        'status': d.status,
        'time': d.created_at.strftime("%b %d, %H:%M")
    } for d in deliveries]
    
    return JsonResponse(data, safe=False)