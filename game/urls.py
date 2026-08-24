from django.urls import path

from . import views

app_name = "game"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("how-it-works/", views.how_it_works, name="how_it_works"),

    path("my-pen/", views.my_pen, name="my_pen"),
    path("collection/", views.collection, name="collection"),
    path("achievements/", views.achievements_view, name="achievements"),

    path("battle/local/setup/", views.local_battle_setup, name="local_setup"),
    path("battle/local/play/", views.local_battle_play, name="local_play"),
    path("battle/local/result/", views.local_battle_result, name="local_result"),
]
