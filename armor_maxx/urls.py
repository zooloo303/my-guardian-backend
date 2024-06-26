# armor_maxx/urls.py
from django.urls import path
from .views import OptimizeArmor

urlpatterns = [
    path('optimize/', OptimizeArmor.as_view(), name='optimize_armor'),
]