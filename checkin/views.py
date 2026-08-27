from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.db.models import Q, F
from django.http import JsonResponse, HttpResponseForbidden
from .models import Post
from .forms import PostForm, PostEditForm

def post_list(request):
    """
    หน้าแรก (Feed) แสดงโพสต์การเช็คอินทั้งหมด
    รองรับการค้นหา (Keyword Search) และกรองเฉพาะโพสต์ที่มีพิกัด GPS
    """
    query = request.GET.get('q', '').strip()
    has_geo = request.GET.get('has_geo')

    posts = Post.objects.select_related('user').all()

    if query:
        posts = posts.filter(
            Q(caption__icontains=query) |
            Q(location_name__icontains=query) |
            Q(user__username__icontains=query)
        )

    if has_geo == '1':
        posts = posts.filter(latitude__isnull=False, longitude__isnull=False)

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

    context = {
        'posts': posts,
        'query': query,
        'has_geo': has_geo,
        'geo_posts_json': geo_posts,
    }
    return render(request, 'checkin/post_list.html', context)

def post_detail(request, pk):
    """
    หน้ารายละเอียดโพสต์เช็คอิน แสดงภาพขนาดเต็ม พิกัด และแผนที่ Interactive
    """
    post = get_object_or_404(Post.objects.select_related('user'), pk=pk)
    
    # เพิ่มยอดวิว
    Post.objects.filter(pk=pk).update(views_count=F('views_count') + 1)
    post.refresh_from_db(fields=['views_count'])

    is_liked = False
    if request.user.is_authenticated:
        is_liked = post.likes.filter(id=request.user.id).exists()

    context = {
        'post': post,
        'is_liked': is_liked,
    }
    return render(request, 'checkin/post_detail.html', context)

@login_required(login_url='login')
def create_post(request):
    """
    View สำหรับการสร้างโพสต์ใหม่ (Create Post View)
    รองรับการอัปโหลดภาพขึ้น Cloudinary และบันทึกพิกัด Geolocation
    """
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
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
    แก้ไขโพสต์ (เฉพาะเจ้าของโพสต์เท่านั้น)
    """
    post = get_object_or_404(Post, pk=pk)
    if post.user != request.user:
        messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขโพสต์นี้')
        return redirect('post_detail', pk=pk)

    if request.method == 'POST':
        form = PostEditForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
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

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'total_likes': post.total_likes})

    return redirect('post_detail', pk=pk)

@login_required(login_url='login')
def my_posts(request):
    """
    หน้าแสดงโพสต์และประวัติการเช็คอินของผู้ใช้งานปัจจุบัน
    """
    posts = Post.objects.filter(user=request.user).order_by('-created_at')
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

def api_posts(request):
    """
    REST API คืนค่า JSON ของโพสต์ที่มีพิกัด สำหรับนำไปวาดแผนที่แบบไดนามิก
    """
    posts = Post.objects.filter(latitude__isnull=False, longitude__isnull=False).select_related('user')[:50]
    data = []
    for p in posts:
        data.append({
            'id': p.id,
            'title': p.location_name or 'สถานที่เช็คอิน',
            'caption': p.caption,
            'lat': float(p.latitude),
            'lng': float(p.longitude),
            'image': p.get_image_url(),
            'author': p.user.username,
            'url': f"/post/{p.id}/"
        })
    return JsonResponse({'status': 'ok', 'count': len(data), 'posts': data})

def register_view(request):
    """
    หน้าสมัครสมาชิก
    """
    if request.user.is_authenticated:
        return redirect('post_list')
        
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'ยินดีต้อนรับสู่ "ที่นี่มีอะไร" คุณ {user.username}! 🌟')
            return redirect('post_list')
        else:
            messages.error(request, 'การลงทะเบียนไม่ถูกต้อง กรุณาตรวจสอบข้อมูล')
    else:
        form = UserCreationForm()
    return render(request, 'checkin/register.html', {'form': form})

def login_view(request):
    """
    หน้าเข้าสู่ระบบ
    """
    if request.user.is_authenticated:
        return redirect('post_list')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'ยินดีต้อนรับกลับ, {username}!')
                next_url = request.GET.get('next', 'post_list')
                return redirect(next_url)
        messages.error(request, 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    else:
        form = AuthenticationForm()
    return render(request, 'checkin/login.html', {'form': form})

def logout_view(request):
    """
    ออกจากระบบ
    """
    logout(request)
    messages.info(request, 'คุณได้ออกจากระบบเรียบร้อยแล้ว')
    return redirect('post_list')
