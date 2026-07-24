from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('',lambda request: redirect('admin/')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Hamari api app ko connect kiya
]
