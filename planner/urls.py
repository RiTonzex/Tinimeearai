from django.urls import path
from . import views

urlpatterns = [
    path('planner/collections/', views.saved_collections, name='saved_collections'),
    path('planner/collections/<int:pk>/map/', views.trip_map_view, name='trip_map_view'),
    path('api/bookmarks/toggle/', views.toggle_bookmark, name='toggle_bookmark'),
    path('api/collections/create/', views.create_collection, name='create_collection'),
    path('api/collections/<int:pk>/edit/', views.edit_collection, name='edit_collection'),
    path('api/collections/<int:pk>/delete/', views.delete_collection, name='delete_collection'),
    path('api/collections/<int:pk>/pins/', views.collection_pins_api, name='collection_pins_api'),
    path('api/collections/', views.get_user_collections_api, name='user_collections_api'),
]
