from django.urls import path

from . import views

urlpatterns = [
    path('', views.lista_chats, name='lista_chats'),
    path('chats/lista/', views.lista_parcial, name='lista_parcial'),
    path('chat/<int:pk>/', views.chat, name='chat'),
    path('chat/<int:pk>/mensajes/', views.chat_mensajes, name='chat_mensajes'),
    path('chat/<int:pk>/enviar/', views.chat_enviar, name='chat_enviar'),
    path('webhook/twilio/', views.webhook_twilio, name='webhook_twilio'),
    path('plantilla/', views.enviar_plantilla, name='enviar_plantilla'),
]
