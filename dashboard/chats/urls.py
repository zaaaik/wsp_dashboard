from django.urls import path

from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('chats/', views.chats, name='chats'),
    path('chats/lista/', views.lista_parcial, name='lista_parcial'),
    path('chat/<int:pk>/', views.chats, name='chat'),
    path('chat/<int:pk>/mensajes/', views.chat_mensajes, name='chat_mensajes'),
    path('chat/<int:pk>/enviar/', views.chat_enviar, name='chat_enviar'),
    path('chat/<int:pk>/notas/', views.chat_notas, name='chat_notas'),
    path('webhook/twilio/', views.webhook_twilio, name='webhook_twilio'),
    path('plantilla/', views.enviar_plantilla, name='enviar_plantilla'),
]
