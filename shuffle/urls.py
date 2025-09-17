from django.urls import path

from shuffle import views

urlpatterns = [
    path("", views.index, name="index"),
]