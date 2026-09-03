import json
import os
import re
import urllib.parse
import requests
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Count, Q, F
from django.http import JsonResponse, HttpResponseForbidden
from django.core.mail import send_mail
from django.core.paginator import Paginator
from .models import Post, PostImage, Comment, Follow, Notification, Profile, Report, PlaceReview, Province, Badge, UserBadge, PasswordResetOTP
from .forms import PostForm, PostEditForm, ThaiUserCreationForm, ProfileUpdateForm, ThaiPasswordChangeForm, CommentForm, ForgotPasswordRequestForm, VerifyOTPOnlyForm, SetNewPasswordForm, DeleteAccountForm
from .utils import calculate_haversine_distance, get_live_weather, validate_image_file, upload_post_image_dedup, upload_user_avatar



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
    if feed_tab not in ('smart', 'following', 'explore', 'top_rated'):
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
    elif feed_tab == 'top_rated' or request.GET.get('sort') == 'top_rated':
        # เรียงตามคะแนนรีวิวสูงสุด (Top Rated)
        posts = list(posts_qs.order_by('-avg_rating', '-review_count', '-created_at'))
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

    # อ่านค่าพิกัดผู้ใช้จาก Query string หรือ Session
    user_lat = request.GET.get('lat')
    user_lng = request.GET.get('lng')
    if user_lat and user_lng:
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
            request.session['user_lat'] = user_lat
            request.session['user_lng'] = user_lng
        except (ValueError, TypeError):
            user_lat = request.session.get('user_lat')
            user_lng = request.session.get('user_lng')
    else:
        user_lat = request.session.get('user_lat')
        user_lng = request.session.get('user_lng')

    nearby = request.GET.get('nearby') == '1'

    # เติมข้อมูลระยะทาง Haversine และสภาพอากาศสด Open-Meteo
    for p in posts:
        if user_lat is not None and user_lng is not None and getattr(p, 'has_coordinates', False):
            p.distance_km = calculate_haversine_distance(user_lat, user_lng, p.latitude, p.longitude)
        else:
            p.distance_km = None

        if getattr(p, 'has_coordinates', False):
            p.weather = get_live_weather(p.latitude, p.longitude)
        else:
            p.weather = None

    # ตัวกรอง "ใกล้ฉัน (< 10km)"
    if nearby and user_lat is not None and user_lng is not None:
        posts = [p for p in posts if p.distance_km is not None and p.distance_km <= 10.0]
        posts.sort(key=lambda x: x.distance_km if x.distance_km is not None else 999999)

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
        'user_lat': user_lat,
        'user_lng': user_lng,
        'nearby': nearby,
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

    user_review = None
    if request.user.is_authenticated:
        from .models import PlaceReview
        user_review = PlaceReview.objects.filter(user=request.user, post=post).first()

    reviews = post.reviews.select_related('user', 'user__profile').all()

    comments = post.comments.filter(is_hidden=False).select_related('user', 'user__profile').all()
    comment_form = CommentForm()

    # คำนวณระยะทางและดึงสภาพอากาศสำหรับหน้ารายละเอียด
    user_lat = request.session.get('user_lat')
    user_lng = request.session.get('user_lng')
    if user_lat is not None and user_lng is not None and getattr(post, 'has_coordinates', False):
        post.distance_km = calculate_haversine_distance(user_lat, user_lng, post.latitude, post.longitude)
    else:
        post.distance_km = None

    if getattr(post, 'has_coordinates', False):
        post.weather = get_live_weather(post.latitude, post.longitude)
    else:
        post.weather = None

    context = {
        'post': post,
        'is_liked': is_liked,
        'is_following': is_following,
        'is_bookmarked': is_bookmarked,
        'comments': comments,
        'comment_form': comment_form,
        'user_review': user_review,
        'reviews': reviews,
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

def detect_province_from_location(location_name, tags=""):
    """
    ตรวจจับจังหวัดอัตโนมัติจากชื่อสถานที่ หรือแท็ก
    """
    if not location_name and not tags:
        return None
    text = f"{location_name or ''} {tags or ''}"
    provinces = Province.objects.all()
    for p in provinces:
        if p.name_th in text or (p.name_en and p.name_en.lower() in text.lower()):
            return p
    return None

def evaluate_badges_for_user(user, new_post=None):
    """
    ตรวจสอบเงื่อนไขและปลดล็อกเหรียญรางวัล (Badge) ให้ผู้ใช้อัตโนมัติ
    คืนค่ารายการเหรียญใหม่ที่เพิ่งได้รับ
    """
    unearned_badges = Badge.objects.exclude(awarded_to__user=user)
    if not unearned_badges.exists():
        return []

    newly_unlocked = []
    user_posts = Post.objects.filter(user=user, is_hidden=False)
    post_count = user_posts.count()
    
    distinct_provinces_count = user_posts.filter(province__isnull=False).values('province').distinct().count()

    for badge in unearned_badges:
        unlocked = False
        config = badge.criteria_config or {}

        if badge.criteria_type == 'POST_COUNT':
            min_count = config.get('min_count', 1)
            if post_count >= min_count:
                unlocked = True

        elif badge.criteria_type == 'PROVINCE_COUNT':
            min_prov = config.get('min_provinces', 1)
            if distinct_provinces_count >= min_prov:
                unlocked = True

        elif badge.criteria_type == 'TAG_COUNT':
            target_tag = config.get('tag', '')
            min_count = config.get('min_count', 1)
            if target_tag:
                tag_matched_posts = user_posts.filter(
                    Q(tags__icontains=target_tag) | Q(caption__icontains=target_tag) | Q(location_name__icontains=target_tag)
                ).count()
                if tag_matched_posts >= min_count:
                    unlocked = True

        elif badge.criteria_type == 'TIME_RANGE':
            start_h = config.get('start_hour', 0)
            end_h = config.get('end_hour', 23)
            min_count = config.get('min_count', 1)
            
            matching_time_count = 0
            for p in user_posts:
                post_hour = p.created_at.hour
                if start_h <= end_h:
                    if start_h <= post_hour <= end_h:
                        matching_time_count += 1
                else:
                    if post_hour >= start_h or post_hour <= end_h:
                        matching_time_count += 1
            if matching_time_count >= min_count:
                unlocked = True

        if unlocked:
            ub, created = UserBadge.objects.get_or_create(
                user=user,
                badge=badge,
                defaults={'related_post': new_post}
            )
            if created:
                newly_unlocked.append(badge)
                Notification.objects.create(
                    recipient=user,
                    actor=user,
                    verb='badge_unlocked',
                    post=new_post
                )

    return newly_unlocked

@login_required(login_url='login')
def create_post(request):
    """
    View สำหรับการสร้างโพสต์ใหม่ (Create Post View)
    รองรับการอัปโหลดรูปภาพหลายรูป (Multi-image Carousel) และบันทึกพิกัด Geolocation
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        uploaded_files = request.FILES.getlist('images') or ([request.FILES['image']] if 'image' in request.FILES else [])

        if not uploaded_files:
            form.add_error('image', 'กรุณาเลือกรูปภาพอย่างน้อย 1 รูปภาพ')
        else:
            for f in uploaded_files:
                is_valid, err_msg = validate_image_file(f, max_size_mb=15)
                if not is_valid:
                    form.add_error('image', err_msg)
                    break

        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user

            # Auto-detect province if provided or matching location
            prov_id = request.POST.get('province')
            if prov_id:
                try:
                    post.province_id = int(prov_id)
                except (ValueError, TypeError):
                    pass
            if not post.province:
                post.province = detect_province_from_location(post.location_name, post.tags)

            # แนวทางที่ 1: อัปโหลดรูปภาพพร้อมระบบ Content Hash Deduplication
            cloudinary_ids = []
            for img_file in uploaded_files:
                c_id = upload_post_image_dedup(img_file)
                cloudinary_ids.append(c_id)

            if cloudinary_ids:
                post.image = cloudinary_ids[0]

            post.save()

            # บันทึกรูปภาพทั้งหมดลงใน PostImage
            for idx, c_id in enumerate(cloudinary_ids):
                PostImage.objects.create(
                    post=post,
                    image=c_id,
                    order=idx
                )

            # บันทึกผู้ร่วมทริปที่ถูกแท็ก (Tagged Co-Travelers)
            raw_tagged_ids = request.POST.getlist('tagged_user_ids') or request.POST.get('tagged_user_ids', '').split(',')
            tagged_ids = []
            for tid in raw_tagged_ids:
                try:
                    val = int(tid)
                    if val != request.user.id:
                        tagged_ids.append(val)
                except (ValueError, TypeError):
                    pass
            
            if tagged_ids:
                post.tagged_users.set(tagged_ids)
                for u_id in tagged_ids:
                    Notification.objects.create(
                        recipient_id=u_id,
                        actor=request.user,
                        verb='post_tagged',
                        post=post
                    )

            # Evaluate Gamification Badges
            new_badges = evaluate_badges_for_user(request.user, new_post=post)
            for b in new_badges:
                messages.success(request, f'🎉 ปลดล็อกเหรียญรางวัลใหม่: "{b.name}"!')

            messages.success(request, 'แชร์ประสบการณ์ "ที่นี่มีอะไร" สำเร็จเรียบร้อยแล้ว! ✨')
            return redirect('post_detail', pk=post.pk)
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลและรูปภาพอีกครั้ง')
    else:
        form = PostForm()

    provinces = Province.objects.all()
    return render(request, 'checkin/create_post.html', {'form': form, 'provinces': provinces})

@login_required(login_url='login')
def post_edit(request, pk):
    """
    แก้ไขโพสต์ (เฉพาะเจ้าของโพสต์เท่านั้น) รองรับการเพิ่มรูปภาพเพิ่มเติมและผู้ร่วมทริป
    """
    post = get_object_or_404(Post.objects.prefetch_related('images', 'tagged_users'), pk=pk)
    if post.user != request.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขโพสต์นี้')
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        uploaded_files = request.FILES.getlist('images') or ([request.FILES['image']] if 'image' in request.FILES else [])

        if uploaded_files:
            for f in uploaded_files:
                is_valid, err_msg = validate_image_file(f, max_size_mb=15)
                if not is_valid:
                    form.add_error('image', err_msg)
                    break

        if form.is_valid():
            post = form.save()
            if uploaded_files:
                current_count = post.images.count()
                for idx, img_file in enumerate(uploaded_files):
                    c_id = upload_post_image_dedup(img_file)
                    PostImage.objects.create(
                        post=post,
                        image=c_id,
                        order=current_count + idx
                    )

            # บันทึกปรับปรุงผู้ร่วมทริปที่ถูกแท็ก (เฉพาะคนที่เพิ่มใหม่จะส่งการแจ้งเตือน)
            existing_tagged_ids = set(post.tagged_users.values_list('id', flat=True))
            raw_tagged_ids = request.POST.getlist('tagged_user_ids') or request.POST.get('tagged_user_ids', '').split(',')
            new_tagged_ids = set()
            for tid in raw_tagged_ids:
                try:
                    val = int(tid)
                    if val != request.user.id:
                        new_tagged_ids.add(val)
                except (ValueError, TypeError):
                    pass
            
            post.tagged_users.set(new_tagged_ids)

            # ส่งการแจ้งเตือนเฉพาะคนที่เพิ่งถูกแท็กใหม่เท่านั้น
            added_ids = new_tagged_ids - existing_tagged_ids
            for u_id in added_ids:
                Notification.objects.create(
                    recipient_id=u_id,
                    actor=request.user,
                    verb='post_tagged',
                    post=post
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

@require_POST
def toggle_like(request, pk):
    """
    กดถูกใจ / ยกเลิกถูกใจโพสต์ (จำกัดเฉพาะ POST request)
    """
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('accept', ''):
            return JsonResponse({'status': 'unauthenticated', 'message': 'กรุณาเข้าสู่ระบบก่อนกดถูกใจ', 'redirect': '/login/'}, status=401)
        return redirect('login')

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
        return JsonResponse({'status': 'success', 'liked': liked, 'total_likes': post.total_likes})

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
                avatar_file = request.FILES['avatar']
                is_valid, err_msg = validate_image_file(avatar_file, max_size_mb=5)
                if not is_valid:
                    messages.error(request, err_msg)
                    return render(request, 'checkin/settings_profile.html', {'form': form, 'profile': profile})
                # แนวทางที่ 2: ผูกชื่อรูปโปรไฟล์กับ User ID
                cloud_avatar = upload_user_avatar(avatar_file, request.user.id)
                profile.avatar = cloud_avatar

            profile.save(update_fields=['display_name', 'bio', 'avatar', 'updated_at'])

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

    tagged_posts = target_user.tagged_posts.select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images').order_by('-created_at')

    # Gamification Footprint Data
    visited_svg_ids = list(Province.objects.filter(posts__user=target_user, posts__is_hidden=False).distinct().values_list('svg_id', flat=True))
    total_provinces = Province.objects.count() or 77
    visited_count = len(visited_svg_ids)
    footprint_percentage = round((visited_count / total_provinces * 100), 1)

    # Gamification Badges Data
    evaluate_badges_for_user(target_user)
    all_badges = Badge.objects.all()
    user_badge_map = {ub.badge_id: ub.awarded_at for ub in UserBadge.objects.filter(user=target_user)}
    
    badge_items = []
    for b in all_badges:
        is_unlocked = b.id in user_badge_map
        badge_items.append({
            'badge': b,
            'unlocked': is_unlocked,
            'awarded_at': user_badge_map[b.id] if is_unlocked else None
        })

    context = {
        'target_user': target_user,
        'profile': profile,
        'posts': target_posts,
        'tagged_posts': tagged_posts,
        'total_posts': total_posts,
        'total_checkins': total_checkins,
        'total_likes_received': total_likes_received,
        'followers_count': profile.followers_count,
        'following_count': profile.following_count,
        'is_following': is_following,
        'geo_posts': geo_posts,
        'public_collections': public_collections,
        'visited_svg_ids': visited_svg_ids,
        'visited_count': visited_count,
        'total_provinces': total_provinces,
        'footprint_percentage': footprint_percentage,
        'badge_items': badge_items,
        'unlocked_badges_count': len(user_badge_map),
        'total_badges_count': len(all_badges),
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

def offline_view(request):
    """
    หน้าแสดงผลเมื่ออยู่ในโหมดออฟไลน์ (PWA Offline Fallback)
    """
    return render(request, 'offline.html')


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
    หน้าเข้าสู่ระบบสำหรับสมาชิกทั่วไป (Member Login)
    บัญชีระดับ Admin / Staff จะไม่สามารถเข้าสู่ระบบผ่านหน้านี้ได้ (เพื่อความปลอดภัยและแยกส่วนการทำงาน)
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_dashboard')
        return redirect('post_list')
        
    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # รองรับการเข้าสู่ระบบด้วย อีเมล
        if '@' in login_input:
            user_by_email = User.objects.filter(email__iexact=login_input).first()
            if user_by_email:
                login_input = user_by_email.username

        user = authenticate(username=login_input, password=password)
        if user is not None:
            # หากเป็น Admin หรือ Staff จะไม่อนุญาตให้ล็อกอินผ่านหน้าสมาชิกทั่วไป (ทำเหมือนไม่มีรหัสนั้นอยู่)
            if user.is_staff or user.is_superuser:
                messages.error(request, 'ชื่อผู้ใช้/อีเมล หรือรหัสผ่านไม่ถูกต้อง')
                return render(request, 'checkin/login.html', {'form': AuthenticationForm(), 'next': request.GET.get('next', '')})

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


def admin_login_view(request):
    """
    หน้าเข้าสู่ระบบสำหรับผู้ดูแลระบบโดยเฉพาะ (Exclusive Admin / Staff Security Portal)
    ไม่อนุญาตให้สมาชิกทั่วไป (Member) เข้าใช้งานผ่านหน้านี้
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_dashboard')
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงส่วนผู้ดูแลระบบ')
        return redirect('post_list')

    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        if '@' in login_input:
            user_by_email = User.objects.filter(email__iexact=login_input).first()
            if user_by_email:
                login_input = user_by_email.username

        user = authenticate(username=login_input, password=password)
        if user is not None:
            # ตรวจสอบสิทธิ์เฉพาะ Staff หรือ Superuser เท่านั้น
            if not user.is_staff and not user.is_superuser:
                messages.error(request, 'สิทธิ์การเข้าถึงถูกปฏิเสธ: หน้านี้สำหรับผู้ดูแลระบบเท่านั้น (Staff Only)')
                return render(request, 'checkin/admin_login.html', {'next': request.GET.get('next', '')})

            if hasattr(user, 'profile') and user.profile.is_banned:
                messages.error(request, 'บัญชีผู้ดูแลนี้ถูกระงับการใช้งาน กรุณาติดต่อ Super Admin')
                return redirect('admin_login')

            login(request, user)
            messages.success(request, f'ยินดีต้อนรับเข้าสู่ระบบจัดการผู้ดูแล, ท่านผู้ดูแล @{user.username} 🛡️')
            next_url = request.POST.get('next') or request.GET.get('next') or 'admin_dashboard'
            return redirect(next_url)
        else:
            messages.error(request, 'ชื่อผู้ใช้ หรือรหัสผ่านผู้ดูแลระบบไม่ถูกต้อง')
    
    return render(request, 'checkin/admin_login.html', {'next': request.GET.get('next', '')})



def forgot_password_view(request):
    """
    ขั้นตอนที่ 1: หน้าขอรับรหัส OTP สำหรับรีเซ็ตรหัสผ่านทางอีเมล
    """
    if request.user.is_authenticated:
        return redirect('post_list')

    if request.method == 'POST':
        form = ForgotPasswordRequestForm(request.POST)
        if form.is_valid():
            user = form.user
            email = user.email.strip()

            # Invalidate previous un-used OTPs
            PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

            # สร้าง OTP 6 หลัก
            otp = PasswordResetOTP.create_otp_for_user(user, email)

            # ส่งอีเมล
            subject = '[ที่นี่มีอะไร] รหัสยืนยันสำหรับรีเซ็ตรหัสผ่านของคุณ'
            message_text = f"""สวัสดีคุณ {user.profile.get_display_name() if hasattr(user, 'profile') else user.username},

คุณได้ทำการขอรีเซ็ตรหัสผ่านสำหรับบัญชี @{user.username} บนระบบ "ที่นี่มีอะไร" (Tinimeearai)

รหัสยืนยัน (OTP) ของคุณคือ: {otp.otp_code}

* ⚠️ รหัสยืนยันนี้มีอายุการใช้งานสำหรับตั้งรหัสผ่านใหม่ กรุณากรอกในหน้าเว็บโดยเร็ว
* หากคุณไม่ได้เป็นผู้ส่งคำขอนี้ กรุณาละเว้นอีเมลฉบับนี้ บัญชีของคุณจะยังคงปลอดภัย

ขอแสดงความนับถือ,
ทีมงาน ที่นี่มีอะไร (Tinimeearai)
"""
            email_sent_ok = False
            try:
                send_mail(
                    subject=subject,
                    message=message_text,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tinimeearai.com'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                email_sent_ok = True
            except Exception as e:
                # Fallback print to server console for dev
                print(f"[Email Notice] Could not send via external SMTP: {e}. [DEV OTP CODE: {otp.otp_code}]")

            # Mask email for UI
            parts = email.split('@')
            name, domain = parts[0], parts[1]
            masked_name = name[0] + '*' * max(1, len(name) - 2) + (name[-1] if len(name) > 1 else '')
            masked_email = f"{masked_name}@{domain}"

            request.session['reset_user_id'] = user.id
            request.session['reset_masked_email'] = masked_email
            request.session['otp_verified'] = False

            if settings.DEBUG and not email_sent_ok:
                messages.info(request, f'🔔 [โหมดพัฒนา] รหัส OTP ของคุณคือ {otp.otp_code}')
            else:
                messages.success(request, f'รหัสยืนยัน 6 หลักถูกส่งไปยัง {masked_email} แล้ว ✉️')
                
            return redirect('verify_reset_otp')
        else:
            messages.error(request, 'กรุณาตรวจสอบข้อมูลที่กรอกอีกครั้ง')
    else:
        form = ForgotPasswordRequestForm()

    return render(request, 'checkin/forgot_password.html', {'form': form})


def resend_reset_otp_view(request):
    """
    API / Endpoint สำหรับขอส่งรหัส OTP ใหม่อีกครั้งทันที
    """
    if request.user.is_authenticated:
        return redirect('post_list')

    user_id = request.session.get('reset_user_id')
    if not user_id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({'success': False, 'error': 'กรุณาระบุชื่อผู้ใช้ก่อนขอรหัส'}, status=400)
        messages.warning(request, 'กรุณาระบุชื่อผู้ใช้ก่อนขอรหัส')
        return redirect('forgot_password')

    user = get_object_or_404(User, pk=user_id)
    email = user.email.strip()

    # Invalidate previous OTPs
    PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

    # Create fresh OTP
    otp = PasswordResetOTP.create_otp_for_user(user, email)

    # Send Email
    subject = '[ที่นี่มีอะไร] รหัสยืนยันใหม่สำหรับรีเซ็ตรหัสผ่านของคุณ'
    message_text = f"""สวัสดีคุณ {user.profile.get_display_name() if hasattr(user, 'profile') else user.username},

รหัสยืนยัน (OTP) ใหม่ของคุณคือ: {otp.otp_code}

* หากคุณไม่ได้เป็นผู้ส่งคำขอนี้ กรุณาละเว้นอีเมลฉบับนี้ บัญชีของคุณจะยังคงปลอดภัย

ขอแสดงความนับถือ,
ทีมงาน ที่นี่มีอะไร (Tinimeearai)
"""
    try:
        send_mail(
            subject=subject,
            message=message_text,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@tinimeearai.com'),
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"[Email Notice] Resend error: {e}. [DEV OTP CODE: {otp.otp_code}]")

    request.session['otp_verified'] = False

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
        return JsonResponse({
            'success': True,
            'message': 'ส่งรหัสยืนยัน OTP ใหม่ไปยังอีเมลของคุณเรียบร้อยแล้ว ✉️',
            'time_remaining': 60
        })

    messages.success(request, 'ส่งรหัสยืนยัน OTP ใหม่เรียบร้อยแล้ว ✉️')
    return redirect('verify_reset_otp')


def verify_reset_otp_view(request):
    """
    ขั้นตอนที่ 2: หน้ากรอกและยืนยันรหัส OTP 6 หลัก (รองรับทั้ง AJAX แบบ Real-time และ Form Submit)
    """
    if request.user.is_authenticated:
        return redirect('post_list')

    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.warning(request, 'กรุณาระบุชื่อผู้ใช้หรืออีเมลก่อนเพื่อรับรหัสยืนยัน')
        return redirect('forgot_password')

    user = get_object_or_404(User, pk=user_id)
    masked_email = request.session.get('reset_masked_email', user.email)

    latest_otp = PasswordResetOTP.objects.filter(
        user=user,
        is_used=False
    ).order_by('-created_at').first()

    time_remaining = latest_otp.time_remaining_seconds(60) if latest_otp else 0

    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '') or request.content_type == 'application/json'

    if request.method == 'POST':
        import json
        post_data = request.POST
        if request.content_type == 'application/json':
            try:
                post_data = json.loads(request.body.decode('utf-8'))
            except Exception:
                post_data = {}

        form = VerifyOTPOnlyForm(user=user, data=post_data)
        if form.is_valid():
            # Mark OTP as used and set session verified flag
            form.otp_record.is_used = True
            form.otp_record.save(update_fields=['is_used'])
            request.session['otp_verified'] = True

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('set_new_password')
                })

            messages.success(request, '✅ ยืนยันรหัส OTP สำเร็จแล้ว! กรุณากำหนดรหัสผ่านใหม่ของคุณ')
            return redirect('set_new_password')
        else:
            err_msg = 'รหัสยืนยัน OTP ไม่ถูกต้อง'
            if form.errors.get('otp_code'):
                err_msg = form.errors['otp_code'][0]

            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': err_msg
                }, status=400)

            messages.error(request, err_msg)
    else:
        form = VerifyOTPOnlyForm(user=user)

    return render(request, 'checkin/forgot_password_verify.html', {
        'form': form,
        'masked_email': masked_email,
        'username': user.username,
        'time_remaining': time_remaining
    })




def set_new_password_view(request):
    """
    ขั้นตอนที่ 3: หน้ากำหนดรหัสผ่านใหม่ (เข้าถึงได้เฉพาะเมื่อผ่านการยืนยัน OTP แล้วเท่านั้น)
    """
    if request.user.is_authenticated:
        return redirect('post_list')

    user_id = request.session.get('reset_user_id')
    is_verified = request.session.get('otp_verified')

    if not user_id or not is_verified:
        messages.warning(request, 'กรุณายืนยันรหัส OTP ให้สำเร็จก่อนตั้งรหัสผ่านใหม่')
        return redirect('forgot_password')

    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = SetNewPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            # Clean session variables
            request.session.pop('reset_user_id', None)
            request.session.pop('reset_masked_email', None)
            request.session.pop('otp_verified', None)
            messages.success(request, '🎉 เปลี่ยนรหัสผ่านใหม่สำเร็จแล้ว! กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่ 🔒')
            return redirect('login')
        else:
            messages.error(request, 'การตั้งรหัสผ่านใหม่ไม่สำเร็จ กรุณาตรวจสอบความถูกต้องของรหัสผ่าน')
    else:
        form = SetNewPasswordForm(user=user)

    return render(request, 'checkin/forgot_password_new_password.html', {
        'form': form,
        'username': user.username
    })



@login_required(login_url='login')
def delete_account_view(request):
    """
    หน้าและฟังก์ชันสำหรับลบบัญชีตนเองถาวร (Danger Zone)
    """
    if request.method == 'POST':
        form = DeleteAccountForm(user=request.user, data=request.POST)
        if form.is_valid():
            username = request.user.username
            logout(request)
            # Delete user account and cascade associated data
            User.objects.filter(username=username).delete()
            messages.info(request, f'บัญชี @{username} และข้อมูลทั้งหมดของคุณถูกลบออกจากระบบเรียบร้อยแล้ว หวังว่าจะได้พบกันใหม่อีกครั้ง')
            return redirect('register')
        else:
            messages.error(request, 'ไม่สามารถลบบัญชีได้ กรุณาตรวจสอบรหัสผ่านและข้อความยืนยัน')
    else:
        form = DeleteAccountForm(user=request.user)

    return render(request, 'checkin/settings_delete_account.html', {'form': form})


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
    ทำเครื่องหมายว่าอ่านแล้ว และเปิดไปยังหน้าที่เกี่ยวข้องอย่างถูกต้องและปลอดภัย
    """
    from .models import Notification
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()

    # หากเป็นการปลดล็อกเหรียญรางวัล นำทางไปดูที่หน้าโปรไฟล์ตนเอง
    if notification.verb == 'badge_unlocked':
        return redirect('user_profile', username=request.user.username)

    # หากเป็นการเริ่มติดตาม นำทางไปดูโปรไฟล์ของผู้ติดตาม
    if notification.verb == 'follow_user' and notification.actor:
        return redirect('user_profile', username=notification.actor.username)

    # หากมีโพสต์ที่เกี่ยวข้อง นำทางไปยังหน้ารายละเอียดโพสต์
    if notification.post:
        try:
            return redirect('post_detail', pk=notification.post.pk)
        except Exception:
            pass

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
    sort_by = request.GET.get('sort_by') or request.GET.get('sort') or 'newest'
    distance_filter = request.GET.get('distance', 'all')

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
    elif sort_by in ('rating', 'top_rated'):
        posts_qs = posts_qs.order_by('-avg_rating', '-review_count', '-created_at')
    else:  # newest
        posts_qs = posts_qs.order_by('-created_at')

    post_results = list(posts_qs.select_related('user', 'user__profile').prefetch_related('likes', 'comments', 'images').distinct())

    user_lat = request.GET.get('lat') or request.session.get('user_lat')
    user_lng = request.GET.get('lng') or request.session.get('user_lng')
    if user_lat and user_lng:
        try:
            user_lat = float(user_lat)
            user_lng = float(user_lng)
            request.session['user_lat'] = user_lat
            request.session['user_lng'] = user_lng
        except (ValueError, TypeError):
            user_lat = request.session.get('user_lat')
            user_lng = request.session.get('user_lng')

    nearby = request.GET.get('nearby') == '1' or (distance_filter not in ('all', '', None))

    for p in post_results:
        if user_lat is not None and user_lng is not None and getattr(p, 'has_coordinates', False):
            p.distance_km = calculate_haversine_distance(user_lat, user_lng, p.latitude, p.longitude)
        else:
            p.distance_km = None

        if getattr(p, 'has_coordinates', False):
            p.weather = get_live_weather(p.latitude, p.longitude)
        else:
            p.weather = None

    # Filter by Distance / Radius
    max_dist_km = None
    if distance_filter and distance_filter != 'all':
        try:
            max_dist_km = float(distance_filter)
        except (ValueError, TypeError):
            max_dist_km = None
    elif nearby:
        max_dist_km = 10.0

    if max_dist_km is not None and user_lat is not None and user_lng is not None:
        post_results = [p for p in post_results if p.distance_km is not None and p.distance_km <= max_dist_km]
        if sort_by == 'distance' or (sort_by == 'newest' and nearby):
            post_results.sort(key=lambda x: x.distance_km if x.distance_km is not None else 999999)

    # Active Filters Count
    has_dist_filter = 1 if (distance_filter and distance_filter != 'all') else 0
    active_filters_count = len(selected_regions) + len(selected_provinces) + len(selected_categories) + (1 if date_range != 'all' else 0) + (1 if sort_by != 'newest' else 0) + has_dist_filter

    context = {
        'query': query,
        'search_type': search_type,
        'sort': sort_by,
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
        'distance_filter': distance_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'sort_by': sort_by,
        'active_filters_count': active_filters_count,
        'user_lat': user_lat,
        'user_lng': user_lng,
        'nearby': nearby,
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

        # อัปเดต Profile display_name และ avatar
        if hasattr(user, 'profile'):
            profile = user.profile
            if not profile.display_name:
                profile.display_name = name or user.username
            
            # ดึงรูปโปรไฟล์จาก Google และอัปโหลดขึ้น Cloudinary เป็นไฟล์ถาวร
            if picture:
                # ปรับขนาดรูปเป็นความละเอียดสูงระดับ HD (400px)
                hd_picture = picture.replace('=s96-c', '=s400-c')
                avatar_str = str(profile.avatar or '')
                # ดึงรูปใหม่หากยังไม่มีรูป หรือรูปเดิมเป็นรูปจาก Google/เกิดปัญหา URL ขาด
                should_update_avatar = (
                    not profile.avatar or 
                    'https://lh3.googleusercontent' in avatar_str or
                    f'avatar_user_{user.id}' in avatar_str
                )
                if should_update_avatar:
                    try:
                        cloud_avatar = upload_user_avatar(hd_picture, user.id)
                        if cloud_avatar:
                            profile.avatar = cloud_avatar
                    except Exception as upload_err:
                        print(f"Error uploading Google avatar to Cloudinary: {upload_err}")
                        if not profile.avatar:
                            profile.avatar = hd_picture

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


def seed_mock_reports_if_empty():
    """
    สร้างข้อมูลการรายงานจำลอง (Mock Reports) เพื่อให้ Admin Dashboard มีข้อมูลให้ทดสอบระบบ
    """
    if Report.objects.count() > 0:
        return

    reporter_user, _ = User.objects.get_or_create(username='traveler_demo', defaults={'first_name': 'นักเดินทางจำลอง'})
    target_user, _ = User.objects.get_or_create(username='suspicious_bot', defaults={'first_name': 'บอทต้องสงสัย'})
    
    sample_posts = list(Post.objects.all()[:3])
    if not sample_posts:
        sample_post = Post.objects.create(
            user=target_user,
            location_name='เว็บพนันออนไลน์ครบวงจร ชวนเที่ยวรับโบนัส',
            caption='แจกเครดิตฟรี แอดไลน์ @fakebonus เลยตอนนี้! คลิกดูสถานที่จัดโปรโมชั่นลับ',
            tags='โปรโมชั่น, เครดิตฟรี, คาเฟ่'
        )
        sample_posts = [sample_post]

    sample_comment = None
    if sample_posts:
        sample_comment, _ = Comment.objects.get_or_create(
            user=target_user,
            post=sample_posts[0],
            defaults={'content': 'รับปั่นยอด วิวเที่ยวแลกเงิน สนใจทักส่วนตัวด่วน!'}
        )

    # 1. รายงานสแปม (Pending)
    Report.objects.create(
        reporter=reporter_user,
        post=sample_posts[0],
        reason='spam',
        status='pending',
        details='โพสต์ข้อความสแปมและชักชวนเข้าเว็บพนัน/โฆษณาไม่เกี่ยวกับสถานที่ท่องเที่ยว'
    )

    # 2. รายงานเนื้อหาไม่เหมาะสม (Pending)
    if len(sample_posts) > 1:
        Report.objects.create(
            reporter=reporter_user,
            post=sample_posts[1],
            reason='inappropriate',
            status='pending',
            details='ภาพประกอบหรือข้อความในโพสต์มีเนื้อหาไม่เหมาะสมต่อเยาวชน'
        )

    # 3. รายงานคอมเมนต์คุกคาม/หยาบคาย (Pending)
    if sample_comment:
        Report.objects.create(
            reporter=reporter_user,
            comment=sample_comment,
            reason='harassment',
            status='pending',
            details='คอมเมนต์ใช้ถ้อยคำก่อกวนและสแปมข้อความในโพสต์ผู้อื่น'
        )

    # 4. รายงานข้อมูลเท็จ (Resolved)
    Report.objects.create(
        reporter=reporter_user,
        post=sample_posts[0],
        reason='fake_news',
        status='resolved',
        details='พิกัดสถานที่คลาดเคลื่อน เจ้าหน้าที่ได้ดำเนินการตรวจสอบและแก้ไขแล้ว'
    )


@login_required(login_url='admin_login')
def admin_dashboard(request):
    """
    หน้า Admin Dashboard สไตล์ Dark Glassmorphism
    รวม Stat Cards 4 ช่อง, กราฟ Chart.js (โพสต์รายวัน และ หมวดหมู่อยอดนิยม),
    Moderation Queue ตารางจัดการรายงาน และ ปุ่มค้นหาผู้ใช้เพื่อสั่งระงับ/แบนบัญชี
    """
    if not request.user.is_staff and not request.user.is_superuser:
        messages.error(request, 'คุณไม่มีสิทธิ์เข้าถึงส่วนผู้ดูแลระบบ')
        return redirect('post_list')

    # Ensure mock reports exist for testing moderation
    seed_mock_reports_if_empty()

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

    # Chart 2: Top Popular Provinces (6 Provinces)
    THAI_PROVINCES = [
        "กรุงเทพมหานคร", "กระบี่", "กาญจนบุรี", "กาฬสินธุ์", "กำแพงเพชร", "ขอนแก่น", 
        "จันทบุรี", "ฉะเชิงเทรา", "ชลบุรี", "ชัยนาท", "ชัยภูมิ", "ชุมพร", 
        "เชียงราย", "เชียงใหม่", "ตรัง", "ตราด", "ตาก", "นครนายก", 
        "นครปฐม", "นครพนม", "นครราชสีมา", "นครศรีธรรมราช", "นครสวรรค์", "นนทบุรี", 
        "นราธิวาส", "น่าน", "บึงกาฬ", "บุรีรัมย์", "ปทุมธานี", "ประจวบคีรีขันธ์", 
        "ปราจีนบุรี", "ปัตตานี", "พระนครศรีอยุธยา", "พะเยา", "พังงา", "พัทลุง", 
        "พิจิตร", "พิษณุโลก", "เพชรบุรี", "เพชรบูรณ์", "แพร่", "ภูเก็ต", 
        "มหาสารคาม", "มุกดาหาร", "แม่ฮ่องสอน", "ยโสธร", "ยะลา", "ร้อยเอ็ด", 
        "ระนอง", "ระยอง", "ราชบุรี", "ลพบุรี", "ลำปาง", "ลำพูน", 
        "เลย", "ศรีสะเกษ", "สกลนคร", "สงขลา", "สตูล", "สมุทรปราการ", 
        "สมุทรสงคราม", "สมุทรสาคร", "สระแก้ว", "สระบุรี", "สิงห์บุรี", "สุโขทัย", 
        "สุพรรณบุรี", "สุราษฎร์ธานี", "สุรินทร์", "หนองคาย", "หนองบัวลำภู", "อ่างทอง", 
        "อำนาจเจริญ", "อุดรธานี", "อุตรดิตถ์", "อุทัยธานี", "อุบลราชธานี"
    ]

    province_counts = {}
    short_words = {"เลย", "ตาก", "แพร่", "น่าน", "ตรัง"}

    for p in Post.objects.all():
        text_to_search = f"{p.location_name or ''} {p.tags or ''} {p.caption or ''}"
        matched_in_post = set()
        for prov in THAI_PROVINCES:
            short_name = prov.replace("พระนครศรีอยุธยา", "อยุธยา").replace("กรุงเทพมหานคร", "กรุงเทพ")
            if prov in short_words:
                pattern = r'(?:จ\.|จังหวัด|#|\s|^)' + re.escape(prov) + r'(?:\s|$|,|\.|\)|\|)'
                if re.search(pattern, text_to_search):
                    matched_in_post.add(prov)
            else:
                if prov in text_to_search or short_name in text_to_search:
                    matched_in_post.add(prov)
        for prov in matched_in_post:
            province_counts[prov] = province_counts.get(prov, 0) + 1

    sorted_provinces = sorted(province_counts.items(), key=lambda x: x[1], reverse=True)[:6]

    default_popular = [('เชียงใหม่', 6), ('สุราษฎร์ธานี', 5), ('กระบี่', 4), ('กรุงเทพมหานคร', 3), ('ภูเก็ต', 2), ('ชลบุรี', 1)]
    final_provinces = list(sorted_provinces)
    existing_names = {p[0] for p in final_provinces}
    for def_name, def_val in default_popular:
        if len(final_provinces) >= 6:
            break
        if def_name not in existing_names:
            final_provinces.append((def_name, def_val))
            existing_names.add(def_name)

    category_labels = [p[0] for p in final_provinces[:6]]
    category_data = [p[1] for p in final_provinces[:6]]

    # Moderation Queue (Reports) - Default filter to 'pending'
    status_filter = request.GET.get('status', 'pending')
    if status_filter not in ('pending', 'resolved', 'dismissed'):
        status_filter = 'pending'

    reports_qs = Report.objects.select_related(
        'reporter', 'reporter__profile',
        'post', 'post__user', 'post__user__profile',
        'comment', 'comment__user', 'comment__user__profile'
    )
    reports = reports_qs.filter(status=status_filter)

    # User Search & Ban Queue with Pagination (10 users per page)
    user_q = request.GET.get('user_q', '').strip()
    users_qs = User.objects.select_related('profile').order_by('-date_joined')
    if user_q:
        clean_q = user_q.lstrip('@').strip()
        users_qs = users_qs.filter(
            Q(username__icontains=user_q) |
            Q(username__icontains=clean_q) |
            Q(email__icontains=user_q) |
            Q(email__icontains=clean_q) |
            Q(profile__display_name__icontains=user_q) |
            Q(profile__display_name__icontains=clean_q)
        ).distinct()

    user_paginator = Paginator(users_qs, 9)
    user_page_number = request.GET.get('user_page', 1)
    users_page = user_paginator.get_page(user_page_number)

    try:
        user_page_range = user_paginator.get_elided_page_range(users_page.number, on_each_side=2, on_ends=1)
    except Exception:
        user_page_range = user_paginator.page_range

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
        'users_list': users_page,
        'users_page': users_page,
        'user_paginator': user_paginator,
        'user_page_range': user_page_range,
        'user_q': user_q,
    }
    return render(request, 'checkin/admin_dashboard.html', context)


@login_required(login_url='login')
@require_POST
def report_item(request):
    """
    API/Form Action ให้ผู้ใช้งานทั่วไปกดส่งรายงานเนื้อหา (Post, Comment หรือ User Profile)
    """
    item_type = request.POST.get('item_type')
    item_id = request.POST.get('item_id')
    reason = request.POST.get('reason', 'other')
    details = request.POST.get('details', '').strip()

    if not item_id or item_type not in ('post', 'comment', 'user'):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'json' in request.content_type:
            return JsonResponse({'success': False, 'message': 'ข้อมูลการรายงานไม่ถูกต้อง'}, status=400)
        messages.error(request, 'ข้อมูลการรายงานไม่ถูกต้อง')
        return redirect('post_list')

    post_obj = None
    comment_obj = None
    reported_user_obj = None

    if item_type == 'post':
        post_obj = get_object_or_404(Post, pk=item_id)
        if Report.objects.filter(reporter=request.user, post=post_obj, status='pending').exists():
            msg = 'คุณได้ส่งรายงานโพสต์นี้ไปแล้ว อยู่ระหว่างการตรวจสอบ'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.info(request, msg)
            return redirect('post_detail', pk=item_id)
    elif item_type == 'comment':
        comment_obj = get_object_or_404(Comment, pk=item_id)
        if Report.objects.filter(reporter=request.user, comment=comment_obj, status='pending').exists():
            msg = 'คุณได้ส่งรายงานความคิดเห็นนี้ไปแล้ว อยู่ระหว่างการตรวจสอบ'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.info(request, msg)
            return redirect('post_detail', pk=comment_obj.post_id)
    elif item_type == 'user':
        if str(item_id).isdigit():
            reported_user_obj = get_object_or_404(User, pk=int(item_id))
        else:
            reported_user_obj = get_object_or_404(User, username=str(item_id).lstrip('@'))

        if reported_user_obj == request.user:
            msg = 'ไม่สามารถรายงานบัญชีของตนเองได้'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': msg}, status=400)
            messages.warning(request, msg)
            return redirect('user_profile', username=request.user.username)

        if Report.objects.filter(reporter=request.user, reported_user=reported_user_obj, status='pending').exists():
            msg = f'คุณได้ส่งรายงานผู้ใช้ @{reported_user_obj.username} ไปแล้ว อยู่ระหว่างการตรวจสอบ'
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': msg})
            messages.info(request, msg)
            return redirect('user_profile', username=reported_user_obj.username)

    Report.objects.create(
        reporter=request.user,
        post=post_obj,
        comment=comment_obj,
        reported_user=reported_user_obj,
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
    elif reported_user_obj:
        return redirect('user_profile', username=reported_user_obj.username)
    return redirect('post_list')


@login_required(login_url='admin_login')
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
        if report.reported_user:
            report.reported_user.profile.is_banned = True
            report.reported_user.profile.save()
        report.status = 'resolved'
        msg = f'ซ่อนเนื้อหา/ระงับสิทธิ์ของรายงาน #{report.id} เรียบร้อยแล้ว'
    elif action == 'delete':
        if report.post:
            report.post.delete()
        elif report.comment:
            report.comment.delete()
        elif report.reported_user:
            report.reported_user.profile.is_banned = True
            report.reported_user.profile.save()
        report.status = 'resolved'
        msg = f'ลบเนื้อหา/ระงับสิทธิ์ของรายงาน #{report.id} เรียบร้อยแล้ว'
    elif action == 'dismiss':
        report.status = 'dismissed'
        msg = f'ปฏิเสธรายงาน #{report.id} เรียบร้อยแล้ว'
    else:
        return JsonResponse({'success': False, 'message': 'คำสั่งไม่ถูกต้อง'}, status=400)

    report.save()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': msg, 'status': report.status, 'status_display': report.get_status_display()})

    messages.success(request, msg)
    referer = request.META.get('HTTP_REFERER')
    if referer and 'admin_dashboard' in referer:
        return redirect(referer)
    return redirect('admin_dashboard')


@login_required(login_url='admin_login')
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
    referer = request.META.get('HTTP_REFERER')
    if referer and 'admin_dashboard' in referer:
        return redirect(referer)
    return redirect('admin_dashboard')


# -----------------------------------------------------------------------------
# Place Rating & Review APIs
# -----------------------------------------------------------------------------
@login_required(login_url='login')
@require_POST
def save_review_api(request):
    """
    API สำหรับสร้างหรือแก้ไขรีวิวสถานที่ (1-5 ดาว)
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        post_id = data.get('post_id')
        score = data.get('score')
        aspect_scenery = data.get('aspect_scenery')
        aspect_transport = data.get('aspect_transport')
        review_text = data.get('review_text', '').strip() if data.get('review_text') else None

        if not post_id:
            return JsonResponse({'status': 'error', 'message': 'กรุณาระบุ post_id'}, status=400)

        post = get_object_or_404(Post, pk=post_id)

        try:
            score = int(score)
            if score < 1 or score > 5:
                return JsonResponse({'status': 'error', 'message': 'คะแนนรวมต้องอยู่ระหว่าง 1-5 ดาว'}, status=400)
        except (TypeError, ValueError):
            return JsonResponse({'status': 'error', 'message': 'คะแนนรวมไม่ถูกต้อง'}, status=400)

        scenery_val = None
        if aspect_scenery:
            try:
                scenery_val = int(aspect_scenery)
                if scenery_val < 1 or scenery_val > 5:
                    scenery_val = None
            except (TypeError, ValueError):
                scenery_val = None

        transport_val = None
        if aspect_transport:
            try:
                transport_val = int(aspect_transport)
                if transport_val < 1 or transport_val > 5:
                    transport_val = None
            except (TypeError, ValueError):
                transport_val = None

        review, created = PlaceReview.objects.update_or_create(
            user=request.user,
            post=post,
            defaults={
                'score': score,
                'aspect_scenery': scenery_val,
                'aspect_transport': transport_val,
                'review_text': review_text,
            }
        )

        post.refresh_from_db(fields=['avg_rating', 'review_count'])

        return JsonResponse({
            'status': 'success',
            'created': created,
            'review_id': review.id,
            'score': review.score,
            'aspect_scenery': review.aspect_scenery,
            'aspect_transport': review.aspect_transport,
            'review_text': review.review_text or '',
            'avg_rating': float(post.avg_rating),
            'review_count': post.review_count,
            'message': 'บันทึกการรีวิวเรียบร้อยแล้ว ⭐' if created else 'อัปเดตรีวิวเรียบร้อยแล้ว ✨'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required(login_url='login')
@require_POST
def delete_review_api(request, pk):
    """
    API สำหรับลบรีวิวสถานที่ (เฉพาะเจ้าของรีวิว)
    """
    try:
        review = get_object_or_404(PlaceReview, pk=pk)
        if review.user != request.user:
            return JsonResponse({'status': 'error', 'message': 'คุณไม่มีสิทธิ์ลบรีวิวนี้'}, status=403)

        post = review.post
        review.delete()
        post.refresh_from_db(fields=['avg_rating', 'review_count'])

        return JsonResponse({
            'status': 'success',
            'avg_rating': float(post.avg_rating),
            'review_count': post.review_count,
            'message': 'ลบรีวิวเรียบร้อยแล้ว'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def get_post_reviews_api(request, pk):
    """
    API คืนรายการรีวิวทั้งหมดของโพสต์
    """
    post = get_object_or_404(Post, pk=pk)
    reviews = post.reviews.select_related('user', 'user__profile').all()

    rev_list = []
    for r in reviews:
        display_name = r.user.username
        avatar_url = None
        if hasattr(r.user, 'profile'):
            display_name = r.user.profile.get_display_name()
            avatar_url = r.user.profile.get_avatar_url()

        rev_list.append({
            'id': r.id,
            'username': r.user.username,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'score': r.score,
            'aspect_scenery': r.aspect_scenery,
            'aspect_transport': r.aspect_transport,
            'review_text': r.review_text or '',
            'created_at': r.created_at.strftime('%d/%m/%Y %H:%M'),
            'is_owner': request.user.is_authenticated and r.user == request.user
        })

    return JsonResponse({
        'status': 'ok',
        'post_id': post.id,
        'avg_rating': float(post.avg_rating),
        'review_count': post.review_count,
        'reviews': rev_list
    })


# -----------------------------------------------------------------------------
# User Search Autocomplete API for Tagging Friends
# -----------------------------------------------------------------------------
@login_required(login_url='login')
def user_search_api(request):
    """
    API ค้นหาผู้ใช้งานสำหรับการแท็กเพื่อนร่วมทริป (@username)
    คืนรายการ JSON List [{id, username, display_name, avatar_url}] จำกัด 10 รายการ
    โดยดันรายชื่อผู้ใช้งานที่กำลังติดตาม (Following/Followers) ขึ้นก่อน
    """
    q = request.GET.get('q', '').strip().lstrip('@')
    current_user = request.user
    following_ids = set(current_user.following_set.values_list('following_id', flat=True))

    if not q:
        users = User.objects.filter(followers_made__follower=current_user).exclude(id=current_user.id).select_related('profile')[:10]
        if not users.exists():
            users = User.objects.exclude(id=current_user.id).select_related('profile')[:10]
    else:
        users = User.objects.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(profile__display_name__icontains=q)
        ).exclude(id=current_user.id).select_related('profile')[:15]

    users_list = []
    for u in users:
        display_name = u.username
        avatar_url = None
        if hasattr(u, 'profile'):
            display_name = u.profile.get_display_name()
            avatar_url = u.profile.get_avatar_url()

        is_followed = u.id in following_ids
        users_list.append({
            'id': u.id,
            'username': u.username,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'is_followed': is_followed,
            'priority': 0 if is_followed else 1
        })

    users_list.sort(key=lambda x: (x['priority'], x['username']))
    return JsonResponse({'status': 'ok', 'users': users_list[:10]})


# -----------------------------------------------------------------------------
# Gamification Footprint & Badges APIs
# -----------------------------------------------------------------------------
def user_footprint_api(request, username):
    """
    API คืนค่าสถิติและ svg_id ของจังหวัดที่ผู้ใช้เคยโพสต์/เช็คอินอย่างน้อย 1 ครั้ง
    """
    target_user = get_object_or_404(User, username=username)
    visited_provinces = Province.objects.filter(posts__user=target_user, posts__is_hidden=False).distinct()
    visited_svg_ids = list(visited_provinces.values_list('svg_id', flat=True))
    total_provinces = Province.objects.count() or 77
    visited_count = len(visited_svg_ids)

    return JsonResponse({
        'status': 'ok',
        'visited': visited_svg_ids,
        'visited_count': visited_count,
        'total_provinces': total_provinces,
        'percentage': round((visited_count / total_provinces * 100), 1) if total_provinces > 0 else 0
    })


def user_badges_api(request, username):
    """
    API คืนค่ารายการเหรียญรางวัลทั้งหมดในระบบ พร้อมสถานะปลดล็อก (unlocked)
    """
    target_user = get_object_or_404(User, username=username)
    user_badge_map = {ub.badge_id: ub.awarded_at for ub in UserBadge.objects.filter(user=target_user)}
    
    all_badges = Badge.objects.all()
    badges_list = []
    for b in all_badges:
        is_unlocked = b.id in user_badge_map
        awarded_at = user_badge_map[b.id].strftime('%d/%m/%Y') if is_unlocked else None
        badges_list.append({
            'id': b.id,
            'code': b.code,
            'name': b.name,
            'description': b.description,
            'icon': b.icon,
            'unlocked': is_unlocked,
            'awarded_at': awarded_at,
        })

    return JsonResponse({
        'status': 'ok',
        'unlocked_count': len(user_badge_map),
        'total_badges': len(all_badges),
        'badges': badges_list
    })


def user_follows_api(request, username):
    """
    API คืนค่ารายการผู้ติดตาม (Followers) และ กำลังติดตาม (Following) ของผู้ใช้งาน
    พร้อมสถานะว่า request.user กำลังติดตามผู้ใช้แต่ละคนหรือไม่
    """
    target_user = get_object_or_404(User, username=username)
    viewer = request.user if request.user.is_authenticated else None
    viewer_following_ids = set(viewer.following_set.values_list('following_id', flat=True)) if viewer else set()

    # 1. ผู้ติดตาม (Followers)
    followers_records = Follow.objects.filter(following=target_user).select_related('follower', 'follower__profile').order_by('-created_at')
    followers_data = []
    for f in followers_records:
        u = f.follower
        avatar_url = u.profile.get_avatar_url() if hasattr(u, 'profile') else None
        display_name = u.profile.get_display_name() if hasattr(u, 'profile') else u.username
        bio = u.profile.bio if hasattr(u, 'profile') else ''
        followers_data.append({
            'id': u.id,
            'username': u.username,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'initial': u.profile.get_initial() if hasattr(u, 'profile') else u.username[:1].upper(),
            'bio': bio or '',
            'is_following': u.id in viewer_following_ids,
            'is_self': bool(viewer and u.id == viewer.id),
            'is_staff': u.is_staff or u.is_superuser,
        })

    # 2. กำลังติดตาม (Following)
    following_records = Follow.objects.filter(follower=target_user).select_related('following', 'following__profile').order_by('-created_at')
    following_data = []
    for f in following_records:
        u = f.following
        avatar_url = u.profile.get_avatar_url() if hasattr(u, 'profile') else None
        display_name = u.profile.get_display_name() if hasattr(u, 'profile') else u.username
        bio = u.profile.bio if hasattr(u, 'profile') else ''
        following_data.append({
            'id': u.id,
            'username': u.username,
            'display_name': display_name,
            'avatar_url': avatar_url,
            'initial': u.profile.get_initial() if hasattr(u, 'profile') else u.username[:1].upper(),
            'bio': bio or '',
            'is_following': u.id in viewer_following_ids,
            'is_self': bool(viewer and u.id == viewer.id),
            'is_staff': u.is_staff or u.is_superuser,
        })

    return JsonResponse({
        'status': 'ok',
        'target_username': target_user.username,
        'followers_count': len(followers_data),
        'following_count': len(following_data),
        'followers': followers_data,
        'following': following_data,
    })


