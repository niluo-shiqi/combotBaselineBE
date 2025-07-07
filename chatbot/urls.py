from django.urls import path
from .views import ChatAPIView, InitialMessageAPIView, ClosingMessageAPIView, \
    LuluInitialMessageAPIView, LuluClosingMessageAPIView, LuluAPIView, RandomEndpointAPIView

urlpatterns = [
    path('random/', RandomEndpointAPIView.as_view(), name='random_endpoint'),
    path('random/initial/', RandomEndpointAPIView.as_view(), name='random_initial'),
    path('random/closing/', RandomEndpointAPIView.as_view(), name='random_closing'),
    path('random/reset/', RandomEndpointAPIView.as_view(), name='random_reset'),
    path('chatbot/', ChatAPIView.as_view(), name='chatbot_api'),
    path('chatbot/initial/', InitialMessageAPIView.as_view(), name='initial_message'),
    path('chatbot/closing/', ClosingMessageAPIView.as_view(), name='closing_message'),
    path('lulu/initial/', LuluInitialMessageAPIView.as_view(), name='lulu_initial_message'),
    path('lulu/closing/', LuluClosingMessageAPIView.as_view(), name='lulu_closing_message'),
    path('lulu/', LuluAPIView.as_view(), name='lulu_chatbot_api'),
]
