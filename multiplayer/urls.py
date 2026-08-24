from django.urls import path

from . import views

app_name = "multiplayer"

urlpatterns = [
    path("room/create/", views.private_room_create, name="room_create"),
    path("room/join/", views.private_room_join, name="room_join"),
    path("room/<str:code>/", views.room_lobby, name="room_lobby"),
    path("room/<str:code>/arena/", views.room_set_arena, name="room_set_arena"),
    path("room/<str:code>/start/", views.room_start, name="room_start"),
    path("room/<str:code>/battle/", views.online_battle, name="online_battle"),
    path("room/<str:code>/status/", views.room_status, name="room_status"),

    path("quick-match/", views.quick_match_search, name="quick_match"),
    path("quick-match/start/", views.quick_match_start, name="quick_match_start"),
    path("quick-match/poll/", views.quick_match_poll, name="quick_match_poll"),
    path("quick-match/cancel/", views.quick_match_cancel, name="quick_match_cancel"),

    path("challenge/<str:username>/", views.challenge_friend, name="challenge_friend"),
]
