from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def health_check(request):
    """Simple health-check endpoint used by Railway and load-balancers."""
    return JsonResponse({"status": "ok", "service": "penfight-arena"})


urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("", include("game.urls")),
    path("accounts/", include("accounts.urls")),
    path("store/", include("store.urls")),
    path("arena/", include("multiplayer.urls")),
]

# Serve media files — both in dev and prod (Daphne handles these fine for
# small-scale deployments; offload to Supabase Storage for high traffic).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / "static")
