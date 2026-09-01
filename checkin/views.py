import os
import urllib.parse
import requests
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Count, Q, F
from django.http import JsonResponse, HttpResponseForbidden
from .models import Post, PostImage, Comment, Follow, Notification, Profile, Report
from .forms import PostForm, PostEditForm, ThaiUserCreationForm, ProfileUpdateForm, ThaiPasswordChangeForm, CommentForm

@login_required(login_url='login')
def post_list(request):
    """
    หน้าแรก (Feed) แสดงโพสต์การเช็คอินทั้งหมด
    รองรับระบบฟีดอัจฉริยะ (Intelligent Smart Feed):
    - 'smart' (🌟 สำหรับคุณ): จัดลำดับฟีดด้วย AI/Smart Ranking ให้โพสต์ของคนที่ Follow ขึ้นก่อน พร้อมถ่วงน้ำหนัก Engagement และความสดใหม่
    - 'following' (👥 กำลังติดตาม): กรองเฉพาะโพสต์ของคนที่กำลังติดตามเท่านั้น
    - 'explore' (🧭 สำรวจทั้งหมด): แสดงโพสต์ล่าสุดทั้งหมดตามเวลา
    """
    # Auto-seed sample posts if database is completely empty
    if not Post.objects.exists():
        try:
            from django.core.management import call_command
            call_command('seed_data')
        except Exception as e:
            print(f"Auto-seed exception: {e}")

    query = request.GET.get('q', '').strip()
    has_geo = request.GET.get('has_geo')
    feed_tab = request.GET.get('feed', 'smart')
    if feed_tab not in ('smart', 'following', 'explore'):
        feed_tab = 'smart'

    posts_qs = Post.objects.filter(is_hidden=False, user__profile__is_banned=False).select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images')

    if query:
        posts_qs = posts_qs.filter(
            Q(caption__icontains=query) |
            Q(location_name__icontains=query) |
            Q(user__username__icontains=query)
        )

    if has_geo == '1':
        posts_qs = posts_qs.filter(latitude__isnull=False, longitude__isnull=False)

    following_ids = list(request.user.following_set.values_list('following_id', flat=True)) if request.user.is_authenticated else []

    if feed_tab == 'following':
        # กรองเฉพาะคนที่ติดตาม
        posts = list(posts_qs.filter(user_id__in=following_ids).order_by('-created_at'))
    elif feed_tab == 'explore':
        # เรียงตามเวลาล่าสุดทั้งหมด
        posts = list(posts_qs.order_by('-created_at'))
    else:
        # ฟีดอัจฉริยะ (Smart AI Feed Ranking)
        # โพสต์ของคนที่ Follow จะได้คะแนน Boost มหาศาล (+1000) ทำให้ขึ้นนำเสมอ
        # ผสานกับ Engagement (Likes, Comments, Views), ความสดใหม่ (Recency) และ Multi-photo Carousel Bonus
        now = timezone.now()
        posts_list = list(posts_qs)
        for p in posts_list:
            is_followed = p.user_id in following_ids
            follow_score = 1000 if is_followed else 0
            
            # Engagement Score
            engagement_score = (p.total_likes * 8) + (p.total_comments * 12) + (p.views_count * 1)
            
            # Multi-photo Carousel Bonus
            media_bonus = 15 if p.has_multiple_images else 0
            
            # Recency Score
            age_hours = max(0, (now - p.created_at).total_seconds() / 3600)
            recency_score = max(0, 500 - (age_hours * 15))
            
            p.is_author_followed = is_followed
            p.smart_feed_score = follow_score + engagement_score + media_bonus + recency_score

        posts_list.sort(key=lambda x: getattr(x, 'smart_feed_score', 0), reverse=True)
        posts = posts_list

    # ข้อมูลพิกัดสำหรับแสดงบน Leaflet Map
    geo_posts = []
    for p in posts:
        if p.has_coordinates:
            geo_posts.append({
                'id': p.id,
                'location_name': p.location_name or 'สถานที่เช็คอิน',
                'caption': p.caption[:80] + '...' if len(p.caption) > 80 else p.caption,
                'lat': float(p.latitude),
                'lng': float(p.longitude),
                'image_url': p.get_image_url(),
                'author': p.user.username,
                'url': f"/post/{p.id}/"
            })

    user_bookmarked_post_ids = set()
    if request.user.is_authenticated:
        try:
            from planner.models import Bookmark
            user_bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True))
        except Exception:
            pass

    context = {
        'posts': posts,
        'query': query,
        'has_geo': has_geo,
        'feed_tab': feed_tab,
        'following_ids': following_ids,
        'geo_posts_json': geo_posts,
        'user_bookmarked_post_ids': user_bookmarked_post_ids,
    }
    return render(request, 'checkin/post_list.html', context)

@login_required(login_url='login')
def post_detail(request, pk):
    """
    หน้ารายละเอียดโพสต์เช็คอิน แสดงภาพขนาดเต็มแบบ Carousel พิกัด และแผนที่ Interactive
    """
    post = get_object_or_404(Post.objects.select_related('user', 'user__profile').prefetch_related('images', 'comments__user', 'comments__likes'), pk=pk)
    
    # เพิ่มยอดวิว
    Post.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    post.refresh_from_db(fields=['views_count'])

    is_liked = False
    is_following = False
    is_bookmarked = False
    if request.user.is_authenticated:
        is_liked = post.likes.filter(id=request.user.id).exists()
        if hasattr(request.user, 'profile') and request.user != post.user:
            is_following = request.user.profile.is_following(post.user)
        try:
            from planner.models import Bookmark
            is_bookmarked = Bookmark.objects.filter(user=request.user, post=post).exists()
        except Exception:
            pass

    comments = post.comments.select_related('user', 'user__profile').all()
    comment_form = CommentForm()

    context = {
        'post': post,
        'is_liked': is_liked,
        'is_following': is_following,
        'is_bookmarked': is_bookmarked,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'checkin/post_detail.html', context)

@login_required(login_url='login')
@require_POST
def add_comment(request, pk):
    """
    เพิ่มความคิดเห็นในโพสต์
    """
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.user = request.user
        comment.save()

        # สร้างการแจ้งเตือนสำหรับเจ้าของโพสต์
        if post.user != request.user:
            from .models import Notification
            Notification.objects.create(
                recipient=post.user,
                actor=request.user,
                verb='comment_post',
                post=post,
                comment=comment
            )

        messages.success(request, 'ส่งความคิดเห็นเรียบร้อยแล้ว! 💬✨')
    else:
        messages.error(request, 'ไม่สามารถส่งความคิดเห็นได้ กรุณาพิมพ์ข้อความ')
    return redirect('post_detail', pk=pk)

@login_required(login_url='login')
def delete_comment(request, pk, comment_id):
    """
    ลบความคิดเห็น (เฉพาะเจ้าของความคิดเห็นหรือเจ้าของโพสต์)
    """
    post = get_object_or_404(Post, pk=pk)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.user == request.user or post.user == request.user:
        comment.delete()
        messages.success(request, 'ลบความคิดเห็นเรียบร้อยแล้ว')
    else:
        messages.error(request, 'คุณไม่มีสิทธิ์ลบความคิดเห็นนี้')
    return redirect('post_detail', pk=pk)

@login_required(login_url='login')
@require_POST
def toggle_comment_like(request, pk, comment_id):
    """
    กดถูกใจ / ยกเลิกถูกใจความคิดเห็น สไตล์ IG (AJAX / POST)
    """
    post = get_object_or_404(Post, pk=pk)
    comment = get_object_or_404(Comment, pk=comment_id, post=post)
    if comment.likes.filter(id=request.user.id).exists():
        comment.likes.remove(request.user)
        liked = False
    else:
        comment.likes.add(request.user)
        liked = True
        # สร้างการแจ้งเตือนสำหรับเจ้าของคอมเมนต์
        if comment.user != request.user:
            from .models import Notification
            Notification.objects.create(
                recipient=comment.user,
                actor=request.user,
                verb='like_comment',
                post=post,
                comment=comment
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').startswith('application/json'):
        return JsonResponse({'liked': liked, 'total_likes': comment.total_likes})

    return redirect('post_detail', pk=pk)

@login_required(login_url='login')
def create_post(request):
    """
    View สำหรับการสร้างโพสต์ใหม่ (Create Post View)
    รองรับการอัปโหลดรูปภาพหลายรูป (Multi-image Carousel) และบันทึกพิกัด Geolocation
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        uploaded_files = request.FILES.getlist('images') or ([request.FILES['image']] if 'image' in request.FILES else [])

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            if uploaded_files and not post.image:
                post.image = uploaded_files[0]
            post.save()

            # บันทึกรูปภาพทั้งหมดลงใน PostImage
            if uploaded_files:
                for idx, img_file in enumerate(uploaded_files):
                    PostImage.objects.create(
                        post=post,
                        image=img_file,
                        order=idx
                    )
            elif post.image:
                PostImage.objects.create(
                    post=post,
                    image=post.image,
                    order=0
                )

            messages.success(request, 'แชร์ประสบการณ์ "ที่นี่มีอะไร" สำเร็จเรียบร้อยแล้ว! ✨')
            return redirect('post_detail', pk=post.pk)
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลและรูปภาพอีกครั้ง')
    else:
        form = PostForm()

    return render(request, 'checkin/create_post.html', {'form': form})

@login_required(login_url='login')
def post_edit(request, pk):
    """
    แก้ไขโพสต์ (เฉพาะเจ้าของโพสต์เท่านั้น) รองรับการเพิ่มรูปภาพเพิ่มเติม
    """
    post = get_object_or_404(Post.objects.prefetch_related('images'), pk=pk)
    if post.user != request.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขโพสต์นี้')
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        uploaded_files = request.FILES.getlist('images') or ([request.FILES['image']] if 'image' in request.FILES else [])

        if form.is_valid():
            post = form.save()
            if uploaded_files:
                current_count = post.images.count()
                for idx, img_file in enumerate(uploaded_files):
                    PostImage.objects.create(
                        post=post,
                        image=img_file,
                        order=current_count + idx
                    )
            messages.success(request, 'อัปเดตข้อมูลโพสต์เรียบร้อยแล้ว 🌟')
            return redirect('post_detail', pk=post.pk)
    else:
        form = PostEditForm(instance=post)

    return render(request, 'checkin/post_edit.html', {'form': form, 'post': post})

@login_required(login_url='login')
def post_delete(request, pk):
    """
    ลบโพสต์ (เฉพาะเจ้าของโพสต์เท่านั้น)
    """
    post = get_object_or_404(Post, pk=pk)
    if post.user != request.user:
        messages.error(request, 'คุณไม่มีสิทธิ์ลบโพสต์นี้')
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'ลบโพสต์เรียบร้อยแล้ว')
        return redirect('post_list')

    return render(request, 'checkin/post_confirm_delete.html', {'post': post})

@login_required(login_url='login')
@require_POST
def toggle_like(request, pk):
    """
    กดถูกใจ / ยกเลิกถูกใจโพสต์ (จำกัดเฉพาะ POST request)
    """
    post = get_object_or_404(Post, pk=pk)
    if post.likes.filter(id=request.user.id).exists():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
        # สร้างการแจ้งเตือนสำหรับเจ้าของโพสต์
        if post.user != request.user:
            from .models import Notification
            Notification.objects.create(
                recipient=post.user,
                actor=request.user,
                verb='like_post',
                post=post
            )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
        return JsonResponse({'liked': liked, 'total_likes': post.total_likes})

    return redirect('post_detail', pk=pk)

@login_required(login_url='login')
def my_posts(request):
    """
    หน้าแสดงโพสต์และประวัติการเช็คอินของผู้ใช้งานปัจจุบัน
    """
    posts = Post.objects.filter(user=request.user).select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images').order_by('-created_at')
    total_checkins = posts.filter(latitude__isnull=False, longitude__isnull=False).count()

    geo_posts = []
    for p in posts:
        if p.has_coordinates:
            geo_posts.append({
                'id': p.id,
                'location_name': p.location_name or 'สถานที่เช็คอิน',
                'caption': p.caption[:80],
                'lat': float(p.latitude),
                'lng': float(p.longitude),
                'image_url': p.get_image_url(),
                'url': f"/post/{p.id}/"
            })

    context = {
        'posts': posts,
        'total_posts': posts.count(),
        'total_checkins': total_checkins,
        'geo_posts_json': geo_posts,
    }
    return render(request, 'checkin/my_posts.html', context)

@login_required(login_url='login')
def settings_view(request):
    """
    หน้าหลักการตั้งค่า (Settings Hub) แสดงข้อมูลโปรไฟล์ สถิติ และเมนูตัวเลือกต่างๆ
    """
    user_posts = Post.objects.filter(user=request.user)
    total_posts = user_posts.count()
    total_checkins = user_posts.filter(latitude__isnull=False, longitude__isnull=False).count()
    total_likes_received = sum(p.likes.count() for p in user_posts)

    context = {
        'total_posts': total_posts,
        'total_checkins': total_checkins,
        'total_likes_received': total_likes_received,
    }
    return render(request, 'checkin/settings.html', context)

@login_required(login_url='login')
def settings_profile_view(request):
    """
    หน้าแก้ไขข้อมูลโปรไฟล์ (Display Name, Bio, ชื่อ นามสกุล อีเมล)
    """
    from .models import Profile
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES)
        if form.is_valid():
            profile.display_name = form.cleaned_data.get('display_name')
            profile.bio = form.cleaned_data.get('bio')
            if 'avatar' in request.FILES and request.FILES['avatar']:
                cloud_key = getattr(settings, 'CLOUDINARY_API_KEY', None) or os.environ.get('CLOUDINARY_API_KEY')
                if cloud_key and cloud_key not in ('your_api_key', 'dummy_api_key'):
                    try:
                        profile.avatar = request.FILES['avatar']
                        profile.save()
                    except Exception:
                        pass
            profile.save(update_fields=['display_name', 'bio', 'updated_at'])

            request.user.first_name = form.cleaned_data.get('first_name')
            request.user.last_name = form.cleaned_data.get('last_name')
            request.user.email = form.cleaned_data.get('email')
            request.user.save()
            messages.success(request, 'บันทึกข้อมูลโปรไฟล์และรูปภาพเรียบร้อยแล้ว! 🌟')
            return redirect('settings')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง')
    else:
        form = ProfileUpdateForm(initial={
            'display_name': profile.display_name,
            'bio': profile.bio,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        })
    return render(request, 'checkin/settings_profile.html', {'form': form, 'profile': profile})

@login_required(login_url='login')
def user_profile_view(request, username):
    """
    หน้าดูโปรไฟล์สาธารณะของผู้ใช้งานคนอื่น (Public Profile View)
    """
    target_user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=target_user)
    
    target_posts = target_user.posts.select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images').order_by('-created_at')
    total_posts = target_posts.count()
    total_checkins = target_posts.filter(latitude__isnull=False, longitude__isnull=False).count()
    total_likes_received = sum(p.likes.count() for p in target_posts)

    is_following = profile.is_followed_by(request.user) if request.user.is_authenticated else False

    geo_posts = []
    for p in target_posts:
        if p.latitude and p.longitude:
            geo_posts.append({
                'id': p.id,
                'location_name': p.location_name or 'จุดเช็คอิน',
                'lat': float(p.latitude),
                'lng': float(p.longitude),
                'image_url': p.get_image_url(),
                'url': f"/post/{p.id}/"
            })

    from planner.models import Collection, Bookmark
    if request.user.is_authenticated and request.user == target_user:
        public_collections = Collection.objects.filter(user=target_user).prefetch_related('bookmarks__post')
    else:
        public_collections = Collection.objects.filter(user=target_user, is_public=True).prefetch_related('bookmarks__post')

    user_bookmarked_post_ids = set()
    if request.user.is_authenticated:
        try:
            user_bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True))
        except Exception:
            pass

    context = {
        'target_user': target_user,
        'profile': profile,
        'posts': target_posts,
        'total_posts': total_posts,
        'total_checkins': total_checkins,
        'total_likes_received': total_likes_received,
        'followers_count': profile.followers_count,
        'following_count': profile.following_count,
        'is_following': is_following,
        'geo_posts': geo_posts,
        'public_collections': public_collections,
        'is_self': (target_user == request.user),
        'user_bookmarked_post_ids': user_bookmarked_post_ids,
    }
    return render(request, 'checkin/user_profile.html', context)

@login_required(login_url='login')
@require_POST
def toggle_follow(request, username):
    """
    กดติดตาม / ยกเลิกติดตามผู้ใช้งาน (Follow / Unfollow Toggle)
    รองรับทั้ง AJAX และ Regular Form Submission
    """
    target_user = get_object_or_404(User, username=username)
    if target_user == request.user:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
        messages.warning(request, 'คุณไม่สามารถติดตามตนเองได้')
        return redirect('user_profile', username=username)

    follow_record = Follow.objects.filter(follower=request.user, following=target_user).first()
    if follow_record:
        follow_record.delete()
        is_following = False
    else:
        Follow.objects.create(follower=request.user, following=target_user)
        is_following = True
        # สร้าง Notification ให้ผู้ถูกติดตาม
        Notification.objects.create(
            recipient=target_user,
            actor=request.user,
            verb='follow_user'
        )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
        return JsonResponse({
            'is_following': is_following,
            'followers_count': target_user.profile.followers_count,
            'following_count': target_user.profile.following_count,
            'username': target_user.username
        })

    return redirect('user_profile', username=username)

@login_required(login_url='login')
def settings_password_view(request):
    """
    หน้าเปลี่ยนรหัสผ่าน
    """
    if request.method == 'POST':
        form = ThaiPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, 'เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว! 🔒✨')
            return redirect('settings')
        else:
            messages.error(request, 'การเปลี่ยนรหัสผ่านไม่สำเร็จ กรุณาตรวจสอบข้อผิดพลาดด้านล่าง')
    else:
        form = ThaiPasswordChangeForm(user=request.user)
    return render(request, 'checkin/settings_password.html', {'password_form': form})

@login_required(login_url='login')
def settings_gps_view(request):
    """
    หน้าตั้งค่าระบบพิกัดและตำแหน่ง GPS
    """
    return render(request, 'checkin/settings_gps.html')

@login_required(login_url='login')
def settings_map_view(request):
    """
    หน้าตั้งค่าสไตล์แผนที่ & การแสดงผล
    """
    return render(request, 'checkin/settings_map.html')

@login_required(login_url='login')
def settings_data_view(request):
    """
    หน้าจัดการข้อมูล สำรองข้อมูล และล้างแคช
    """
    return render(request, 'checkin/settings_data.html')

@login_required(login_url='login')
def settings_about_view(request):
    """
    หน้าเกี่ยวกับแอปพลิเคชัน
    """
    return render(request, 'checkin/settings_about.html')

@login_required(login_url='login')
def export_user_data(request):
    """
    ส่งออกข้อมูลการเดินทางและโพสต์ทั้งหมดของผู้ใช้เป็นไฟล์ JSON สำรองข้อมูล
    """
    posts = Post.objects.filter(user=request.user).prefetch_related('images').order_by('-created_at')
    posts_data = []
    for p in posts:
        posts_data.append({
            'id': p.id,
            'location_name': p.location_name,
            'caption': p.caption,
            'latitude': float(p.latitude) if p.latitude else None,
            'longitude': float(p.longitude) if p.longitude else None,
            'images': p.get_all_image_urls(),
            'views_count': p.views_count,
            'total_likes': p.total_likes,
            'created_at': p.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        })
    export_payload = {
        'app': 'ที่นี่มีอะไร (TINIMEEARAI)',
        'username': request.user.username,
        'email': request.user.email,
        'date_joined': request.user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if request.user.date_joined else None,
        'total_posts': len(posts_data),
        'posts': posts_data,
    }
    response = JsonResponse(export_payload, json_dumps_params={'ensure_ascii': False, 'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="tinimeearai_backup_{request.user.username}.json"'
    return response

@login_required(login_url='login')
def api_posts(request):
    """
    REST API คืนค่า JSON ของโพสต์ที่มีพิกัด สำหรับนำไปวาดแผนที่แบบไดนามิก
    """
    posts = Post.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related('user').prefetch_related('images')[:50]
    data = []
    for p in posts:
        data.append({
            'id': p.id,
            'title': p.location_name or 'สถานที่เช็คอิน',
            'caption': p.caption,
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'image': p.get_image_url(),
            'images': p.get_all_image_urls(),
            'author': p.user.username,
            'url': f"/post/{p.id}/"
        })
    return JsonResponse({'status': 'ok', 'count': len(data), 'posts': data})

def register_view(request):
    """
    หน้าสมัครสมาชิก (ใช้ ThaiUserCreationForm ข้อความแจ้งเตือนภาษาไทย)
    """
    if request.user.is_authenticated:
        return redirect('post_list')
        
    if request.method == 'POST':
        form = ThaiUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับสู่ "ที่นี่มีอะไร" คุณ {user.username}! 🌟')
            return redirect('post_list')
        else:
            messages.error(request, 'ข้อมูลการสมัครสมาชิกไม่ถูกต้อง กรุณาตรวจสอบคำแนะนำด้านล่าง')
    else:
        form = ThaiUserCreationForm()
    return render(request, 'checkin/register.html', {'form': form})

def login_view(request):
    """
    หน้าเข้าสู่ระบบ (รองรับทั้งการกรอก Username หรือ Email)
    """
    if request.user.is_authenticated:
        return redirect('post_list')
        
    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # รองรับการเข้าสู่ระบบด้วย อีเมล (ถ้ามีเครื่องหมาย @ หรือตรงกับอีเมลในระบบ)
        if '@' in login_input:
            user_by_email = User.objects.filter(email__iexact=login_input).first()
            if user_by_email:
                login_input = user_by_email.username

        user = authenticate(username=login_input, password=password)
        if user is not None:
            if hasattr(user, 'profile') and user.profile.is_banned:
                messages.error(request, 'บัญชีของคุณถูกระงับการใช้งานเนื่องจากละเมิดกฎชุมชน กรุณาติดต่อผู้ดูแลระบบ')
                return redirect('login')
            login(request, user)
            display_name = user.profile.get_display_name() if hasattr(user, 'profile') else user.username
            messages.success(request, f'ยินดีต้อนรับกลับ, {display_name}!')
            next_url = request.POST.get('next') or request.GET.get('next') or 'post_list'
            return redirect(next_url)
        else:
            messages.error(request, 'ชื่อผู้ใช้/อีเมล หรือรหัสผ่านไม่ถูกต้อง')
    else:
        form = AuthenticationForm()

    return render(request, 'checkin/login.html', {'form': form, 'next': request.GET.get('next', '')})


def logout_view(request):
    """
    ออกจากระบบ
    """
    logout(request)
    messages.info(request, 'คุณได้ออกจากระบบเรียบร้อยแล้ว')
    return redirect('login')

@login_required(login_url='login')
def notifications_view(request):
    """
    หน้ารายการแจ้งเตือนของผู้ใช้
    ค่าเริ่มต้นแสดงเฉพาะการแจ้งเตือนที่ยังไม่ได้ดู (is_read=False)
    เมื่อผู้ใช้กดดูแล้ว รายการจะถูกทำเครื่องหมายว่าอ่านแล้ว และจะไม่แสดงในรายการใหม่อีก
    """
    from .models import Notification
    tab = request.GET.get('tab', 'unread')
    if tab not in ('unread', 'all'):
        tab = 'unread'
        
    total_unread = Notification.objects.filter(recipient=request.user, is_read=False).count()
    total_all = Notification.objects.filter(recipient=request.user).count()

    base_qs = Notification.objects.filter(recipient=request.user).select_related(
        'actor', 'actor__profile', 'post', 'comment'
    ).order_by('-created_at')

    if tab == 'all':
        notifications = base_qs
    else:
        notifications = base_qs.filter(is_read=False)

    context = {
        'notifications': notifications,
        'tab': tab,
        'total_unread': total_unread,
        'total_all': total_all,
    }
    return render(request, 'checkin/notifications.html', context)

@login_required(login_url='login')
def mark_notification_read(request, pk):
    """
    ทำเครื่องหมายว่าอ่านแล้ว และเปิดไปยังโพสต์ที่เกี่ยวข้อง
    หลังจากกดดูแล้ว การแจ้งเตือนนี้จะไม่แสดงในรายการใหม่อีก
    """
    from .models import Notification
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    if notification.post:
        return redirect('post_detail', pk=notification.post.pk)
    return redirect('notifications')

@login_required(login_url='login')
def delete_notification(request, pk):
    """
    ลบการแจ้งเตือนออกจากระบบ
    """
    from .models import Notification
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.delete()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').startswith('application/json'):
        return JsonResponse({'success': True})
    return redirect('notifications')

@login_required(login_url='login')
@require_POST
def mark_all_notifications_read(request):
    """
    ทำเครื่องหมายว่าอ่านแล้วทั้งหมด
    """
    from .models import Notification
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('accept', '').startswith('application/json'):
        return JsonResponse({'success': True})
    messages.success(request, 'ทำเครื่องหมายว่าอ่านแล้วทั้งหมดเรียบร้อยแล้ว ✨')
    return redirect('notifications')

# 77 จังหวัด และ 6 ภูมิภาคในประเทศไทย (Thailand 77 Provinces & 6 Regions Mapping)
THAI_REGION_PROVINCES = {
    'north': {
        'name': 'ภาคเหนือ',
        'provinces': ['เชียงใหม่', 'เชียงราย', 'แม่ฮ่องสอน', 'ลำปาง', 'ลำพูน', 'น่าน', 'พะเยา', 'แพร่', 'อุตรดิตถ์']
    },
    'central': {
        'name': 'ภาคกลาง',
        'provinces': ['กรุงเทพมหานคร', 'กรุงเทพ', 'นนทบุรี', 'ปทุมธานี', 'สมุทรปราการ', 'พระนครศรีอยุธยา', 'อยุธยา', 'อ่างทอง', 'ลพบุรี', 'สิงห์บุรี', 'ชัยนาท', 'สระบุรี', 'นครนายก', 'สุพรรณบุรี', 'นครปฐม', 'สมุทรสาคร', 'สมุทรสงคราม', 'กำแพงเพชร', 'นครสวรรค์', 'พิจิตร', 'พิษณุโลก', 'เพชรบูรณ์', 'สุโขทัย', 'อุทัยธานี']
    },
    'northeast': {
        'name': 'ภาคอีสาน (ตะวันออกเฉียงเหนือ)',
        'provinces': ['นครราชสีมา', 'โคราช', 'บุรีรัมย์', 'สุรินทร์', 'ศรีสะเกษ', 'อุบลราชธานี', 'ยโสธร', 'ชัยภูมิ', 'อำนาจเจริญ', 'บึงกาฬ', 'หนองบัวลำภู', 'ขอนแก่น', 'อุดรธานี', 'เลย', 'หนองคาย', 'มหาสารคาม', 'ร้อยเอ็ด', 'กาฬสินธุ์', 'สกลนคร', 'นครพนม', 'มุกดาหาร']
    },
    'south': {
        'name': 'ภาคใต้',
        'provinces': ['ภูเก็ต', 'สุราษฎร์ธานี', 'กระบี่', 'พังงา', 'สงขลา', 'นครศรีธรรมราช', 'ชุมพร', 'ระนอง', 'ตรัง', 'พัทลุง', 'สตูล', 'ปัตตานี', 'ยะลา', 'นราธิวาส', 'เกาะสมุย', 'เกาะพะงัน', 'เกาะพีพี']
    },
    'east': {
        'name': 'ภาคตะวันออก',
        'provinces': ['ชลบุรี', 'พัทยา', 'ระยอง', 'จันทบุรี', 'ตราด', 'ฉะเชิงเทรา', 'ปราจีนบุรี', 'สระแก้ว', 'เกาะเสม็ด', 'เกาะช้าง']
    },
    'west': {
        'name': 'ภาคตะวันตก',
        'provinces': ['กาญจนบุรี', 'ตาก', 'เพชรบุรี', 'ประจวบคีรีขันธ์', 'หัวหิน', 'ราชบุรี']
    }
}

ALL_THAI_PROVINCES = [
    'กรุงเทพมหานคร', 'กระบี่', 'กาญจนบุรี', 'กาฬสินธุ์', 'กำแพงเพชร', 'ขอนแก่น', 'จันทบุรี', 'ฉะเชิงเทรา',
    'ชลบุรี', 'ชัยนาท', 'ชัยภูมิ', 'ชุมพร', 'เชียงราย', 'เชียงใหม่', 'ตรัง', 'ตราด', 'ตาก', 'นครนายก',
    'นครปฐม', 'นครพนม', 'นครราชสีมา', 'นครศรีธรรมราช', 'นครสวรรค์', 'นนทบุรี', 'นราธิวาส', 'น่าน',
    'บึงกาฬ', 'บุรีรัมย์', 'ปทุมธานี', 'ประจวบคีรีขันธ์', 'ปราจีนบุรี', 'ปัตตานี', 'พะเยา', 'พระนครศรีอยุธยา',
    'พังงา', 'พัทลุง', 'พิจิตร', 'พิษณุโลก', 'เพชรบุรี', 'เพชรบูรณ์', 'แพร่', 'ภูเก็ต', 'มหาสารคาม',
    'มุกดาหาร', 'แม่ฮ่องสอน', 'ยโสธร', 'ยะลา', 'ร้อยเอ็ด', 'ระนอง', 'ระยอง', 'ราชบุรี', 'ลพบุรี',
    'ลำปาง', 'ลำพูน', 'เลย', 'ศรีสะเกษ', 'สกลนคร', 'สงขลา', 'สตูล', 'สมุทรปราการ', 'สมุทรสงคราม',
    'สมุทรสาคร', 'สระแก้ว', 'สระบุรี', 'สิงห์บุรี', 'สุโขทัย', 'สุพรรณบุรี', 'สุราษฎร์ธานี', 'สุรินทร์',
    'หนองคาย', 'หนองบัวลำภู', 'อ่างทอง', 'อำนาจเจริญ', 'อุดรธานี', 'อุตรดิตถ์', 'อุทัยธานี', 'อุบลราชธานี'
]

POPULAR_CATEGORIES = [
    'คาเฟ่', 'ทะเล', 'ภูเขา', 'จุดชมวิว', 'ร้านอาหาร', 'วัด', 'พิกัดลับ', 'แคมป์ปิ้ง', 'โฮมสเตย์', 'น้ำตก', 'ตลาดคนเดิน'
]

@login_required(login_url='login')
def search_view(request):
    """
    หน้าค้นหาขั้นสูง (Advanced Search Hub)
    รองรับการค้นหาแยกตาม 77 จังหวัด, 6 ภูมิภาค, หมวดหมู่/แท็ก, ช่วงวันที่ และเรียงลำดับผลลัพธ์
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'posts')
    if search_type not in ('posts', 'accounts'):
        search_type = 'posts'

    selected_regions = request.GET.getlist('regions')
    selected_provinces = request.GET.getlist('provinces')
    selected_categories = request.GET.getlist('categories')
    date_range = request.GET.get('date_range', 'all')
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    sort_by = request.GET.get('sort_by', 'newest')

    posts_qs = Post.objects.all()
    if hasattr(Post, 'is_hidden'):
        posts_qs = posts_qs.filter(is_hidden=False)
    if hasattr(Profile, 'is_banned'):
        posts_qs = posts_qs.filter(user__profile__is_banned=False)
    account_results = []

    # 1. Text Keyword Filter
    if query:
        posts_qs = posts_qs.filter(
            Q(caption__icontains=query) |
            Q(location_name__icontains=query) |
            Q(tags__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__profile__display_name__icontains=query)
        )

        account_results = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__display_name__icontains=query) |
            Q(profile__bio__icontains=query)
        ).select_related('profile').prefetch_related('posts').distinct()

    user_bookmarked_post_ids = set()
    if request.user.is_authenticated:
        try:
            from planner.models import Bookmark
            user_bookmarked_post_ids = set(Bookmark.objects.filter(user=request.user).values_list('post_id', flat=True))
        except Exception:
            pass

    # 2. Region Filter (ภูมิภาค)
    if selected_regions:
        region_provinces_list = []
        for r in selected_regions:
            if r in THAI_REGION_PROVINCES:
                region_provinces_list.extend(THAI_REGION_PROVINCES[r]['provinces'])
        if region_provinces_list:
            region_q = Q()
            for p in region_provinces_list:
                region_q |= Q(location_name__icontains=p) | Q(caption__icontains=p)
            posts_qs = posts_qs.filter(region_q)

    # 3. Province Filter (77 จังหวัด)
    if selected_provinces:
        prov_q = Q()
        for prov in selected_provinces:
            if prov.strip():
                prov_q |= Q(location_name__icontains=prov.strip()) | Q(caption__icontains=prov.strip())
        posts_qs = posts_qs.filter(prov_q)

    # 4. Category / Tag Filter
    if selected_categories:
        cat_q = Q()
        for cat in selected_categories:
            if cat.strip():
                cat_q |= Q(tags__icontains=cat.strip()) | Q(caption__icontains=cat.strip())
        posts_qs = posts_qs.filter(cat_q)

    # 5. Date Range Filter (ช่วงวันที่)
    today = timezone.now().date()
    if date_range == 'today':
        posts_qs = posts_qs.filter(created_at__date=today)
    elif date_range == '7days':
        posts_qs = posts_qs.filter(created_at__date__gte=today - timezone.timedelta(days=7))
    elif date_range == '30days':
        posts_qs = posts_qs.filter(created_at__date__gte=today - timezone.timedelta(days=30))
    elif date_range == 'custom':
        from datetime import datetime
        if start_date_str:
            try:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                posts_qs = posts_qs.filter(created_at__date__gte=start_dt)
            except ValueError:
                pass
        if end_date_str:
            try:
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                posts_qs = posts_qs.filter(created_at__date__lte=end_dt)
            except ValueError:
                pass

    # 6. Sorting / Ordering
    if sort_by == 'popular':
        posts_qs = posts_qs.annotate(num_likes=Count('likes')).order_by('-num_likes', '-created_at')
    elif sort_by == 'views':
        posts_qs = posts_qs.order_by('-views_count', '-created_at')
    elif sort_by == 'comments':
        posts_qs = posts_qs.annotate(num_comments=Count('comments')).order_by('-num_comments', '-created_at')
    else:  # newest
        posts_qs = posts_qs.order_by('-created_at')

    post_results = posts_qs.select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images').distinct()

    # Active Filters Count
    active_filters_count = len(selected_regions) + len(selected_provinces) + len(selected_categories) + (1 if date_range != 'all' else 0) + (1 if sort_by != 'newest' else 0)

    context = {
        'query': query,
        'search_type': search_type,
        'post_results': post_results,
        'account_results': account_results,
        'user_bookmarked_post_ids': user_bookmarked_post_ids,
        'thai_regions': THAI_REGION_PROVINCES,
        'all_provinces': ALL_THAI_PROVINCES,
        'popular_categories': POPULAR_CATEGORIES,
        'selected_regions': selected_regions,
        'selected_provinces': selected_provinces,
        'selected_categories': selected_categories,
        'date_range': date_range,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'sort_by': sort_by,
        'active_filters_count': active_filters_count,
    }
    return render(request, 'checkin/search.html', context)


# -----------------------------------------------------------------------------
# Google OAuth 2.0 Authentication Views
# -----------------------------------------------------------------------------
def google_login(request):
    """
    เริ่มต้นกระบวนการล็อกอินด้วย Google OAuth 2.0
    สร้าง Auth URL และ Redirect ผู้ใช้ไปยังหน้ายินยอมของ Google
    """
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
    if not client_id or client_id in ('your_google_client_id', 'dummy_google_client_id'):
        messages.info(request, 'ระบบ Google OAuth ยังไม่ได้เปิดใช้งาน หรือยังไม่ได้ตั้งค่า GOOGLE_CLIENT_ID ใน .env')
        return redirect('login')

    redirect_uri = request.build_absolute_uri('/auth/google/callback/')
    if not settings.DEBUG and redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'online',
        'prompt': 'select_account',
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)


def google_callback(request):
    """
    Callback URL ที่ Google จะส่ง Authorization Code กลับมาหลังจากผู้ใช้กดยินยอม
    นำ Code ไปแลก Access Token และดึงข้อมูล Profile (Email, Name, Avatar) เพื่อ Login หรือสร้าง User อัตโนมัติ
    """
    code = request.GET.get('code')
    error = request.GET.get('error')

    if error or not code:
        messages.error(request, 'การเข้าสู่ระบบด้วย Google ถูกยกเลิกหรือไม่สำเร็จ')
        return redirect('login')

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '') or os.environ.get('GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '') or os.environ.get('GOOGLE_CLIENT_SECRET', '')
    redirect_uri = request.build_absolute_uri('/auth/google/callback/')
    if not settings.DEBUG and redirect_uri.startswith('http://'):
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)

    # 1. แลก Authorization Code เป็น Access Token
    token_url = 'https://oauth2.googleapis.com/token'
    token_payload = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    try:
        token_res = requests.post(token_url, data=token_payload, timeout=10)
        token_data = token_res.json()
        access_token = token_data.get('access_token')

        if not access_token:
            err_msg = token_data.get('error_description') or 'ไม่สามารถรับ Access Token จาก Google ได้'
            messages.error(request, f'การยืนยันตัวตนผิดพลาด: {err_msg}')
            return redirect('login')

        # 2. ดึงข้อมูล Profile จาก Google UserInfo API
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        userinfo_res = requests.get(userinfo_url, headers={'Authorization': f'Bearer {access_token}'}, timeout=10)
        user_info = userinfo_res.json()

        email = user_info.get('email')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')

        if not email:
            messages.error(request, 'ไม่พบบัญชีอีเมลที่ผูกกับ Google')
            return redirect('login')

        # 3. ตรวจสอบหรือสร้าง User ในระบบ
        user = User.objects.filter(email=email).first()
        if not user:
            # สร้าง username จากส่วนหน้าของ email
            base_username = email.split('@')[0]
            clean_username = "".join(c for c in base_username if c.isalnum() or c in ('_', '-'))
            username = clean_username or "google_user"
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{clean_username}_{counter}"
                counter += 1

            first_name = name.split(' ')[0] if name else username
            last_name = ' '.join(name.split(' ')[1:]) if (name and len(name.split(' ')) > 1) else ''

            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save()

        # อัปเดต Profile display_name และ avatar ถ้ายังไม่มี
        if hasattr(user, 'profile'):
            profile = user.profile
            if not profile.display_name:
                profile.display_name = name or user.username
            if not profile.avatar and picture:
                profile.avatar = picture
            profile.save()

        if hasattr(user, 'profile') and user.profile.is_banned:
            messages.error(request, 'บัญชีของคุณถูกระงับการใช้งานเนื่องจากละเมิดกฎชุมชน กรุณาติดต่อผู้ดูแลระบบ')
            return redirect('login')

        login(request, user)
        messages.success(request, f'เข้าสู่ระบบด้วย Google สำเร็จ! ยินดีต้อนรับคุณ {user.profile.get_display_name()} 🌟')
        return redirect('post_list')

    except Exception as e:
        messages.error(request, f'เกิดข้อผิดพลาดในการเชื่อมต่อกับ Google: {e}')
        return redirect('login')


@login_required(login_url='login')
def admin_dashboard(request):
    """
    หน้า Admin Dashboard สไตล์ Dark Glassmorphism
    รวม Stat Cards 4 ช่อง, กราฟ Chart.js (โพสต์รายวัน และ หมวดหมู่อยอดนิยม),
    Moderation Queue ตารางจัดการรายงาน และ ปุ่มค้นหาผู้ใช้เพื่อสั่งระงับ/แบนบัญชี
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงส่วนผู้ดูแลระบบ')
        return redirect('post_list')

    # Stat Cards
    total_posts = Post.objects.count()
    today_posts = Post.objects.filter(created_at__date=timezone.now().date()).count()
    total_users = User.objects.count()
    banned_users = Profile.objects.filter(is_banned=True).count()
    pending_reports = Report.objects.filter(status='pending').count()
    total_reports = Report.objects.count()
    total_comments = Comment.objects.count()

    # Chart 1: Daily Posts (Last 7 Days)
    today = timezone.now().date()
    daily_posts_labels = []
    daily_posts_data = []
    for i in range(6, -1, -1):
        day = today - timezone.timedelta(days=i)
        count = Post.objects.filter(created_at__date=day).count()
        daily_posts_labels.append(day.strftime('%d/%m'))
        daily_posts_data.append(count)

    # Chart 2: Top Categories / Tags
    tag_counts = {}
    for p in Post.objects.exclude(tags__isnull=True).exclude(tags=''):
        if p.tags:
            split_tags = [t.strip('# ').strip() for t in p.tags.replace(',', ' ').split() if t.strip()]
            for tag in split_tags:
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    if sorted_tags:
        category_labels = [t[0] for t in sorted_tags]
        category_data = [t[1] for t in sorted_tags]
    else:
        category_labels = ['คาเฟ่', 'ทะเล', 'ภูเขา', 'จุดชมวิว', 'ที่เที่ยวลับ']
        category_data = [5, 4, 3, 2, 1]

    # Moderation Queue (Reports)
    status_filter = request.GET.get('status', 'all')
    reports_qs = Report.objects.select_related(
        'reporter', 'reporter__profile',
        'post', 'post__user', 'post__user__profile',
        'comment', 'comment__user', 'comment__user__profile'
    )
    if status_filter in ('pending', 'resolved', 'dismissed'):
        reports = reports_qs.filter(status=status_filter)
    else:
        reports = reports_qs.all()

    # User Search & Ban Queue
    user_q = request.GET.get('user_q', '').strip()
    if user_q:
        users_list = User.objects.select_related('profile').filter(
            Q(username__icontains=user_q) |
            Q(email__icontains=user_q) |
            Q(profile__display_name__icontains=user_q)
        ).order_by('-date_joined')[:20]
    else:
        users_list = User.objects.select_related('profile').order_by('-date_joined')[:10]

    context = {
        'total_posts': total_posts,
        'today_posts': today_posts,
        'total_users': total_users,
        'banned_users': banned_users,
        'pending_reports': pending_reports,
        'total_reports': total_reports,
        'total_comments': total_comments,
        'daily_posts_labels_json': daily_posts_labels,
        'daily_posts_data_json': daily_posts_data,
        'category_labels_json': category_labels,
        'category_data_json': category_data,
        'reports': reports,
        'status_filter': status_filter,
        'users_list': users_list,
        'user_q': user_q,
    }
    return render(request, 'checkin/admin_dashboard.html', context)


@login_required(login_url='login')
@require_POST
def report_item(request):
    """
    API/Form Action ให้ผู้ใช้งานทั่วไปกดส่งรายงานเนื้อหา (Post หรือ Comment)
    """
    item_type = request.POST.get('item_type')
    item_id = request.POST.get('item_id')
    reason = request.POST.get('reason', 'other')
    details = request.POST.get('details', '').strip()

    if not item_id or item_type not in ('post', 'comment'):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'json' in request.content_type:
            return JsonResponse({'success': False, 'message': 'ข้อมูลการรายงานไม่ถูกต้อง'}, status=400)
        messages.error(request, 'ข้อมูลการรายงานไม่ถูกต้อง')
        return redirect('post_list')

    post_obj = None
    comment_obj = None
    if item_type == 'post':
        post_obj = get_object_or_404(Post, pk=item_id)
        if Report.objects.filter(reporter=request.user, post=post_obj, status='pending').exists():
            msg = 'คุณได้ส่งรายงานโพสต์นี้ไปแล้ว อยู่ระหว่างการตรวจสอบ'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.info(request, msg)
            return redirect('post_detail', pk=item_id)
    else:
        comment_obj = get_object_or_404(Comment, pk=item_id)
        if Report.objects.filter(reporter=request.user, comment=comment_obj, status='pending').exists():
            msg = 'คุณได้ส่งรายงานความคิดเห็นนี้ไปแล้ว อยู่ระหว่างการตรวจสอบ'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.info(request, msg)
            return redirect('post_detail', pk=comment_obj.post_id)

    Report.objects.create(
        reporter=request.user,
        post=post_obj,
        comment=comment_obj,
        reason=reason,
        details=details,
        status='pending'
    )

    success_msg = 'ส่งรายงานเรียบร้อยแล้ว ทีมงานจะทำการตรวจสอบโดยเร็วที่สุด'
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': success_msg})

    messages.success(request, success_msg)
    if post_obj:
        return redirect('post_detail', pk=post_obj.pk)
    elif comment_obj:
        return redirect('post_detail', pk=comment_obj.post_id)
    return redirect('post_list')


@login_required(login_url='login')
@require_POST
def admin_resolve_report(request, report_id):
    """
    Action สำหรับแอดมิน: ดำเนินการกับรายงาน (hide/delete/dismiss)
    """
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง'}, status=403)

    report = get_object_or_404(Report, pk=report_id)
    action = request.POST.get('action')

    if action == 'hide':
        if report.post:
            report.post.is_hidden = True
            report.post.save()
        if report.comment:
            report.comment.is_hidden = True
            report.comment.save()
        report.status = 'resolved'
        msg = f'ซ่อนเนื้อหาของรายงาน #{report.id} เรียบร้อยแล้ว'
    elif action == 'delete':
        if report.post:
            report.post.delete()
        elif report.comment:
            report.comment.delete()
        report.status = 'resolved'
        msg = f'ลบเนื้อหาของรายงาน #{report.id} เรียบร้อยแล้ว'
    elif action == 'dismiss':
        report.status = 'dismissed'
        msg = f'ปฏิเสธรายงาน #{report.id} เรียบร้อยแล้ว'
    else:
        return JsonResponse({'success': False, 'message': 'คำสั่งไม่ถูกต้อง'}, status=400)

    report.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': msg, 'status': report.status, 'status_display': report.get_status_display()})

    messages.success(request, msg)
    return redirect('admin_dashboard')


@login_required(login_url='login')
@require_POST
def admin_toggle_ban_user(request, user_id):
    """
    Action สำหรับแอดมิน: สั่งระงับบัญชี/ปลดระงับผู้ใช้งาน (Ban/Unban User)
    """
    if not request.user.is_staff and not request.user.is_superuser:
        return JsonResponse({'success': False, 'message': 'ไม่มีสิทธิ์เข้าถึง'}, status=403)

    target_user = get_object_or_404(User, pk=user_id)
    if target_user == request.user:
        return JsonResponse({'success': False, 'message': 'คุณไม่สามารถสั่งระงับบัญชีของตนเองได้'}, status=400)

    profile = target_user.profile
    profile.is_banned = not profile.is_banned
    profile.save()

    status_str = "ถูกระงับบัญชี (Banned)" if profile.is_banned else "ปกติตามเดิม (Active)"
    msg = f"อัปเดตสถานะบัญชี @{target_user.username} เป็น {status_str} เรียบร้อยแล้ว"

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_banned': profile.is_banned, 'message': msg})

    messages.success(request, msg)
    return redirect('admin_dashboard')


