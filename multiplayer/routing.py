from django.urls import re_path

from multiplayer.consumers.battle_consumer import BattleConsumer

websocket_urlpatterns = [
    re_path(r"^ws/battle/(?P<code>[\w-]+)/$", BattleConsumer.as_asgi()),
]
