import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from checkin.models import Post
from .models import Collection, Bookmark


@login_required(login_url='login')
def saved_collections(request):
    """
    หน้าแสดงรายการคอลเลกชัน / โฟลเดอร์ทริปทั้งหมดของผู้ใช้
    """
    collections = Collection.objects.filter(user=request.user).prefetch_related('bookmarks__post')
    
    # ดึงการบันทึกแบบทั่วไป (ไม่ระบุคอลเลกชัน)
    general_bookmarks = Bookmark.objects.filter(
        user=request.user, 
        collection__isnull=True
    ).select_related('post', 'post__user', 'post__user__profile')
    
    context = {
        'collections': collections,
        'general_bookmarks_count': general_bookmarks.count(),
        'general_bookmarks': general_bookmarks,
    }
    return render(request, 'saved_collections.html', context)


@login_required(login_url='login')
@require_POST
def create_collection(request):
    """
    API สร้างคอลเลกชันใหม่
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            is_public = bool(data.get('is_public', False))
        else:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            is_public = request.POST.get('is_public') in ('true', '1', 'on', True)

        if not title:
            return JsonResponse({'status': 'error', 'message': 'กรุณาระบุชื่อคอลเลกชัน'}, status=400)

        collection = Collection.objects.create(
            user=request.user,
            title=title,
            description=description,
            is_public=is_public
        )
        if 'cover_image' in request.FILES and request.FILES['cover_image']:
            collection.cover_image = request.FILES['cover_image']
            collection.save()

        return JsonResponse({
            'status': 'success',
            'collection': {
                'id': collection.id,
                'title': collection.title,
                'description': collection.description or '',
                'is_public': collection.is_public,
                'posts_count': 0,
                'pins_count': 0,
                'cover_url': collection.get_cover_image_url(),
                'map_url': reverse('trip_map_view', kwargs={'pk': collection.pk})
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def trip_map_view(request, pk):
    """
    หน้าแสดงแผนที่รวม (Trip Map View) สำหรับหมุดทั้งหมดในคอลเลกชัน
    """
    collection = get_object_or_404(Collection, pk=pk)

    # Permission check: เจ้าของ หรือ เป็นสาธารณะ
    if collection.user != request.user and not collection.is_public:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์เข้าถึงคอลเลกชันส่วนตัวนี้")

    context = {
        'collection': collection,
        'is_owner': request.user.is_authenticated and collection.user == request.user,
    }
    return render(request, 'trip_map.html', context)


def collection_pins_api(request, pk):
    """
    API คืนค่า JSON รายการหมุดที่มีพิกัดสำหรับนำไปแสดงบน Leaflet Map
    """
    collection = get_object_or_404(Collection, pk=pk)

    # Permission check
    if collection.user != request.user and not collection.is_public:
        return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิ์เข้าถึงคอลเลกชันนี้'}, status=403)

    bookmarks = collection.bookmarks.select_related('post', 'post__user', 'post__user__profile').filter(
        post__latitude__isnull=False,
        post__longitude__isnull=False
    )

    pins = []
    for bm in bookmarks:
        p = bm.post
        user_display = p.user.username
        if hasattr(p.user, 'profile') and p.user.profile.get_display_name():
            user_display = p.user.profile.get_display_name()

        pins.append({
            'post_id': p.id,
            'title': p.location_name or f"โพสต์ของ {user_display}",
            'caption': p.caption or '',
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'thumbnail_url': p.get_image_url(),
            'location_name': p.location_name or '',
            'detail_url': reverse('post_detail', kwargs={'pk': p.pk}),
            'user_name': user_display,
            'created_at': p.created_at.strftime('%d/%m/%Y'),
        })

    return JsonResponse({
        'status': 'ok',
        'collection': {
            'id': collection.id,
            'title': collection.title,
            'description': collection.description or '',
            'is_public': collection.is_public,
            'total_pins': len(pins)
        },
        'pins': pins
    })


@login_required(login_url='login')
@require_POST
def toggle_bookmark(request):
    """
    API เพิ่ม/ลบ Bookmark ของโพสต์ ( Toggle )
    รองรับทั้งบันทึกทั่วไป และระบุคอลเลกชัน
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            post_id = data.get('post_id')
            collection_id = data.get('collection_id')
        else:
            post_id = request.POST.get('post_id')
            collection_id = request.POST.get('collection_id')

        if not post_id:
            return JsonResponse({'status': 'error', 'message': 'กรุณาระบุ post_id'}, status=400)

        post = get_object_or_404(Post, pk=post_id)
        collection = None

        if collection_id:
            collection = get_object_or_404(Collection, pk=collection_id, user=request.user)

        bookmark_qs = Bookmark.objects.filter(
            user=request.user,
            post=post,
            collection=collection
        )

        if bookmark_qs.exists():
            bookmark_qs.delete()
            bookmarked = False
        else:
            Bookmark.objects.create(
                user=request.user,
                post=post,
                collection=collection
            )
            bookmarked = True

        # Check if bookmarked anywhere by this user
        is_bookmarked_any = Bookmark.objects.filter(user=request.user, post=post).exists()
        user_saved_collection_ids = list(
            Bookmark.objects.filter(user=request.user, post=post, collection__isnull=False)
            .values_list('collection_id', flat=True)
        )

        return JsonResponse({
            'status': 'ok',
            'bookmarked': bookmarked,
            'is_bookmarked_any': is_bookmarked_any,
            'post_id': post.id,
            'collection_id': collection.id if collection else None,
            'saved_collection_ids': user_saved_collection_ids
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required(login_url='login')
@require_GET
def get_user_collections_api(request):
    """
    API ดึงรายการคอลเลกชันของผู้ใช้สำหรับนำไปแสดงใน Dropdown/Modal เลือกคอลเลกชัน
    """
    post_id = request.GET.get('post_id')
    collections = Collection.objects.filter(user=request.user)
    
    saved_collection_ids = []
    is_general_saved = False

    if post_id:
        saved_collection_ids = list(
            Bookmark.objects.filter(user=request.user, post_id=post_id, collection__isnull=False)
            .values_list('collection_id', flat=True)
        )
        is_general_saved = Bookmark.objects.filter(user=request.user, post_id=post_id, collection__isnull=True).exists()

    col_list = []
    for col in collections:
        col_list.append({
            'id': col.id,
            'title': col.title,
            'posts_count': col.posts_count,
            'is_saved': col.id in saved_collection_ids
        })

    return JsonResponse({
        'status': 'ok',
        'collections': col_list,
        'is_general_saved': is_general_saved,
        'post_id': int(post_id) if post_id and post_id.isdigit() else None
    })


@login_required(login_url='login')
@require_POST
def delete_collection(request, pk):
    """
    API ลบคอลเลกชัน/โฟลเดอร์ทริป
    """
    try:
        collection = get_object_or_404(Collection, pk=pk)
        if collection.user != request.user:
            return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิ์ลบคอลเลกชันนี้'}, status=403)

        collection.delete()
        return JsonResponse({
            'status': 'success',
            'message': 'ลบคอลเลกชันเรียบร้อยแล้ว'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required(login_url='login')
@require_POST
def edit_collection(request, pk):
    """
    API แก้ไขข้อมูลคอลเลกชัน (ชื่อ, คำอธิบาย, สถานะสาธารณะ)
    """
    try:
        collection = get_object_or_404(Collection, pk=pk)
        if collection.user != request.user:
            return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิ์แก้ไขคอลเลกชันนี้'}, status=403)

        if request.content_type == 'application/json':
            data = json.loads(request.body)
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            is_public = bool(data.get('is_public', False))
        else:
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            is_public = request.POST.get('is_public') in ('true', '1', 'on', True)

        if not title:
            return JsonResponse({'status': 'error', 'message': 'กรุณาระบุชื่อคอลเลกชัน'}, status=400)

        collection.title = title
        collection.description = description
        collection.is_public = is_public
        if 'cover_image' in request.FILES and request.FILES['cover_image']:
            collection.cover_image = request.FILES['cover_image']
        collection.save()

        return JsonResponse({
            'status': 'success',
            'collection': {
                'id': collection.id,
                'title': collection.title,
                'description': collection.description or '',
                'is_public': collection.is_public,
                'posts_count': collection.posts_count,
                'pins_count': collection.pins_count,
            }
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

