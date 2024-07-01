from app2.models import Notification

def notification_count(request):
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(patient=request.user, is_read=False).count()
    else:
        unread_notifications_count = 0
    return {
        'unread_notifications_count': unread_notifications_count,
    }
