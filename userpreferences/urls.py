from . import views
from django.urls import path

urlpatterns = [
    path('preferences/', views.index, name='preferences'),
]
