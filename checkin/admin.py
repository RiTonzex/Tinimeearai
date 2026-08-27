from django.contrib import admin
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('user', 'location_name', 'latitude', 'longitude', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('caption', 'location_name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
