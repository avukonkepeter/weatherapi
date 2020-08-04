from django import forms
from django.forms import widgets


from weatherapi.models import WeatherAPI


class WeatherAPIForm(forms.ModelForm):

    class Meta:
        fields = '__all__'


class LandingPageForm(forms.Form):
    city = forms.CharField(
        required=True, help_text="The city to search"
    )
    weather_apis = forms.ModelMultipleChoiceField(
        queryset=WeatherAPI.objects.filter(userapi=True).all(),
        required=True,
        help_text="The weather API's to query"
    )
    start_date = forms.DateField(
        help_text="Please enter the end_date for your query",
    )
    end_date = forms.DateField(
        help_text="Please enter the end date for your query"
    )

    class Meta:
        fields = '__all__'