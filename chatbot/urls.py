from django.urls import path
from .views import ChatAPIView, InitialMessageAPIView, ClosingMessageAPIView, NikeInitialMessageAPIView, \
    NikeClosingMessageAPIView, LuluInitialMessageAPIView, LuluClosingMessageAPIView, NikeAPIView, LuluAPIView

urlpatterns = [
    path('chatbot/', ChatAPIView.as_view(), name='chatbot_api'),
    path('chatbot/initial/', InitialMessageAPIView.as_view(), name='initial_message'),
    path('chatbot/closing/', ClosingMessageAPIView.as_view(), name='closing_message'),
    path('nike/initial/', NikeInitialMessageAPIView.as_view(), name='nike_initial_message'),
    path('nike/closing/', NikeClosingMessageAPIView.as_view(), name='nike_closing_message'),
    path('nike/', NikeAPIView.as_view(), name='nike_chatbot_api'),
    path('lulu/initial/', LuluInitialMessageAPIView.as_view(), name='lulu_initial_message'),
    path('lulu/closing/', LuluClosingMessageAPIView.as_view(), name='nike_initial_message'),
    path('lulu/', LuluAPIView.as_view(), name='lulu_initial_message'),
]
