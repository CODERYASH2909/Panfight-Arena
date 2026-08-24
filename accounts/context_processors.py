def notifications(request):
    """Makes unread notification count/list available on every template."""
    if not request.user.is_authenticated:
        return {}
    qs = request.user.notifications.filter(is_read=False)[:8]
    return {
        "nav_notifications": qs,
        "nav_notifications_count": request.user.notifications.filter(is_read=False).count(),
    }
