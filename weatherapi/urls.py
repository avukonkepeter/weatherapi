from django.contrib import admin
from django.urls import path, include
from django.conf.urls import url

from rest_framework.routers import DefaultRouter


from weatherapi import views

router = DefaultRouter()
router.register(
    prefix=r'weatherview',
    viewset=views.WeatherView,
    basename='weatherview'
)
router.register(r'cityautocomplete', views.CityAutocomplete, basename='cityautocomplete')

urlpatterns = [
    path('weatherhistory/', views.WeatherHistoryView.as_view(), name="weather-history"),
    path('admin/', admin.site.urls),
    path(r'api/weatherview', views.WeatherView.as_view(), name="weatherview"),
    path(r'api/', include(router.urls)),
    path('', views.LandingPage.as_view(), name='landing-page')
]
