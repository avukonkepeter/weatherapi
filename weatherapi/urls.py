from django.contrib import admin
from django.urls import path, include


from rest_framework.routers import DefaultRouter


from weatherapi import views


router = DefaultRouter()
router.register(
    prefix=r'weatherview',
    viewset=views.WeatherView,
    basename='weatherview'
)

urlpatterns = [
    path('weatherhistory/', views.WeatherHistoryView.as_view(), name="weather-history"),
    path('admin/', admin.site.urls),
    path(r'api/weatherview', views.WeatherView.as_view(), name="weatherview"),
    path(r'api/locations/<str:city>/', views.WeatherView.as_view(), name="weatherview-get"),
    path(r'api/', include(router.urls)),
    path('', views.LandingPage.as_view(), name='landing-page')
]
