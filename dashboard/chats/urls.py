from django.urls import path

from . import views

urlpatterns = [
    path('webhook/twilio/', views.webhook_twilio, name='webhook_twilio'),
]
