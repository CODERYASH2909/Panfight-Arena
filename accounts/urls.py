from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),

    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("profile/<str:username>/", views.profile_detail, name="profile"),

    path("friends/", views.friends_list, name="friends"),
    path("friends/request/<str:username>/", views.send_friend_request, name="send_friend_request"),
    path("friends/respond/<int:request_id>/<str:action>/", views.respond_friend_request, name="respond_friend_request"),
    path("friends/remove/<str:username>/", views.remove_friend, name="remove_friend"),

    path("notifications/<int:notif_id>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="mark_all_notifications_read"),
]
