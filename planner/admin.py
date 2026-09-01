from django.contrib import admin
from .models import Collection, Bookmark


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_public', 'posts_count', 'pins_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('title', 'description', 'user__username')


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'collection', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'post__caption', 'collection__title')
