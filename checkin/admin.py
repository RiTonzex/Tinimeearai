from django.contrib import admin
from .models import Post, PostImage, Comment, Profile, Notification

class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'location_name', 'latitude', 'longitude', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('caption', 'location_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PostImageInline]

@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('post', 'order', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'verb', 'is_read', 'created_at')
