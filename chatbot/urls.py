from django.urls import path
from .views_refactored import (
    ChatAPIView, InitialMessageAPIView, ClosingMessageAPIView,
    LuluAPIView, LuluInitialMessageAPIView, LuluClosingMessageAPIView,
    RandomEndpointAPIView, memory_status
)

urlpatterns = [
    path('chat/', ChatAPIView.as_view(), name='chat'),
    path('random/initial/', InitialMessageAPIView.as_view(), name='initial_message'),
    path('random/closing/', ClosingMessageAPIView.as_view(), name='closing_message'),
    path('lulu/', LuluAPIView.as_view(), name='lulu_chat'),
    path('lulu/initial/', LuluInitialMessageAPIView.as_view(), name='lulu_initial'),
    path('lulu/closing/', LuluClosingMessageAPIView.as_view(), name='lulu_closing'),
    path('random/', RandomEndpointAPIView.as_view(), name='random_endpoint'),
    path('memory-status/', memory_status, name='memory_status'),
]
