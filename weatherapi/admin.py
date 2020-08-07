from django.contrib import admin


from weatherapi.models import WeatherAPI
from weatherapi.forms import WeatherAPIForm


@admin.register(WeatherAPI)
class WeatherAPIAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'url', 'userapi']
    form = WeatherAPIForm
