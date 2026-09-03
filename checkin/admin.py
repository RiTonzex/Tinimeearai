from django.contrib import admin
from .models import Post, PostImage, Comment, Profile, Notification, Report, PasswordResetOTP, PlaceReview

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'location_name', 'latitude', 'longitude', 'is_hidden', 'created_at')
    list_filter = ('is_hidden', 'created_at', 'user')
    search_fields = ('caption', 'location_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PostImageInline]

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'order', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'is_hidden', 'created_at')
    list_filter = ('is_hidden', 'created_at')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'is_banned', 'created_at')
    list_filter = ('is_banned', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'verb', 'is_read', 'created_at')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'reporter', 'post', 'comment', 'reason', 'status', 'created_at')
    list_filter = ('status', 'reason', 'created_at')
    search_fields = ('reporter__username', 'details', 'post__caption', 'comment__content')

@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'email', 'otp_code', 'is_used', 'created_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'email', 'otp_code')


