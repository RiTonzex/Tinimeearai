from .models import Notification

def notifications_processor(request):
    """
    Context processor เพื่อส่งจำนวนการแจ้งเตือนที่ยังไม่ได้อ่านไปยัง Template แบบรวดเร็ว
    """
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return {
            'unread_notifications_count': unread_count,
        }
    return {
        'unread_notifications_count': 0,
    }

