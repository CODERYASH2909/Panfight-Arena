import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "penfight.settings")

# django_asgi_app must be created before importing anything that touches
# models, so Django's app registry is ready first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
import multiplayer.routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(multiplayer.routing.websocket_urlpatterns))
        ),
    }
)
