from accounts.models import Notification


def notifications_processor(request):
    """Make notifications available in all templates."""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
        # Bell dropdown shows only 3 most recent
        bell_notifications = Notification.objects.filter(user=request.user)[:3]
        return {
            'notifications': bell_notifications,
            'unread_notification_count': unread_count,
        }
    return {}

