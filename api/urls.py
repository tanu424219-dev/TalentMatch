from django.urls import path
from .views import match_resources

urlpatterns = [
    # Yahan <int:client_id> client ki ID pass karega views.py ko
    path('match-resources/<int:client_id>/', match_resources, name='match-resources'),
]