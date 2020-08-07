from datetime import datetime, timedelta


from django import forms
from django.forms import widgets
from django.conf import settings


from weatherapi.models import WeatherAPI


class WeatherAPIForm(forms.ModelForm):

    class Meta:
        model = WeatherAPI
        fields = '__all__'


class LandingPageForm(forms.Form):
    city = forms.CharField(
        required=True, help_text="The city to search for"
    )
    weather_apis = forms.ModelMultipleChoiceField(
        queryset=WeatherAPI.objects.filter(userapi=True).all(),
        required=True,
        help_text="The weather API's to query"
    )
    start_date = forms.DateField(
        help_text="Please enter the start_date for your query | Format: 'YYYY-MM-DD' | Default: 'Todays date'",
        widget=widgets.DateInput(
            format='%Y-%m-%d',
            attrs={
                'placeholder': 'YYYY-MM-DD',
                'value': datetime.strftime(
                    datetime.today(),
                    format='%Y-%m-%d'
                )
            }
        )
    )
    end_date = forms.DateField(
        help_text="Please enter the end date for your query | Format: 'YYYY-MM-DD' | Default: 'One week into the future'",
        widget=widgets.DateInput(
            format='%Y-%m-%d',
            attrs={
                'placeholder': 'YYYY-MM-DD',
                'value': datetime.strftime(
                    datetime.today() + timedelta(days=settings.DEFAULT_QUERY_DURATION_DAYS),
                    format='%Y-%m-%d'
                )
            }
        )
    )

    class Meta:
        fields = '__all__'