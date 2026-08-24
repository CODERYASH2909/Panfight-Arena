from django.urls import path

from . import views

app_name = "store"

urlpatterns = [
    path("", views.store_home, name="home"),
    path("buy/<int:skin_id>/", views.buy_skin, name="buy_skin"),
]
