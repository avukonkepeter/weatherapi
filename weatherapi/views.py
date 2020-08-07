from datetime import datetime, timedelta, date
from statistics import median, mean


from django.shortcuts import render
from django import http
from django.views import View
from django.forms import ValidationError


from rest_framework.views import APIView
from rest_framework import status


from weatherapi.forms import LandingPageForm
from weatherapi.models import WeatherAPI, WeatherAPIRequestRecord


# Ideally we want API views separate from the normal views

class APIViewToViewsetMixin(object):
    @classmethod
    def get_extra_actions(cls):
        return []


class LandingPage(View):
    form_class = LandingPageForm
    template_name = 'templates/index.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})


class CityAutocomplete(APIView, APIViewToViewsetMixin):
    pass


class WeatherView(APIView, APIViewToViewsetMixin):
    """
    Accept a POST request with 'City' and 'Period' information.

    Return json response with 'min', 'max', 'average', 'median' temperature
    as received from the weather API
    """

    def get(self):
        response_data = {
            'msg': "Please POST 'period' and 'city' to this endpoint to "
                   "receive weather data"
        }
        return http.JsonResponse(
            response_data,
            status=status.HTTP_400_BAD_REQUEST
        )

    def post(self, request, *args, **kwargs):
        data = request.data

        form = LandingPageForm(data=data)
        # Standard django validation
        if not form.is_valid():
            return render(request, 'index.html', {'form': form})

        # Determine date is in correct format
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        short_circuit = lambda form: render(request, 'index.html', {'form': form})

        # TODO: Support end_date < start_date, reverse dates, do request and
        #  return results in reverse
        if end_date < start_date:
            form.add_error(
                '',
                ValidationError(
                    "Please Ensure that the 'start_date' is greater than the 'end_date'"
                )
            )
            return short_circuit(form)

        if end_date - start_date > timedelta(days=10):
            form.add_error(
                '',
                ValidationError(
                    "App currently doesn't support weather forecasts for "
                    "more than 10 days"
                )
            )
            return short_circuit(form)

        # Determine whether to forecast or get historical data
        weather_lookup = 'historical' if start_date < date.today() else 'forecast'

        if weather_lookup == 'historical':
            # temporarily disable historical functionality till further notice
            form.add_error(
                'start_date',
                ValidationError(
                    "App will not be supporting historical lookups due to "
                    "API constraints. Historical weather lookups will return "
                    "an error until further notice"
                )
            )
            return short_circuit(form)

        date_diff = end_date - start_date

        # For some reason yyyy/mm/3 - yyyy/mm/1 would give you 2 as answer,
        # but if you count in days it would be 3, jitter by 1
        date_diff = date_diff.days + 1
        # Diff offset used to return days relative to today (future)
        date_diff_offset = start_date - date.today()
        date_diff_offset = date_diff_offset.days

        if end_date > start_date + timedelta(days=10):
            form.add_error(
                '',
                ValidationError(
                    "App currently doesn't support weather forecasts for "
                    "more than 10 days into the future"
                )
            )
            return short_circuit(form)
        data = {}

        yahoo_weather = WeatherAPI.get_yahoo_results(city=form.cleaned_data['city'])

        # Verify data is valid against Yahoo API, yahoo has fuzzy goodness :S
        # This helps while autocomplete is not complete
        if not yahoo_weather:
            form.add_error(
                '',
                ValidationError(
                    'We could not find a match for the city you entered. '
                    'Please make sure you\'ve entered the city name correctly'
                )
            )
            return short_circuit(form)

        # We have a city
        api_city = yahoo_weather.location.city
        # City info
        data['city'] = api_city
        # Check if user entered city exactly as what we returned: Indicate
        # this is a fuzzy result
        user_city_as_array = [
            user_city_verb.lower() for user_city_verb in
            form.cleaned_data['city'].strip().split()
            if user_city_verb
        ]
        api_city_as_array = [
            api_city_verb.lower() for api_city_verb in api_city.strip().split()
        ]
        data['cities_match'] = user_city_as_array == api_city_as_array
        data['city_info'] = {
            k: v for k, v in yahoo_weather.location.__dict__.items() if k not in [
                'woeid', 'city']
        }

        data['forecast'] = {}
        data['forecast']['min_values'] = []
        data['forecast']['max_values'] = []

        data['forecast']['humidity_values'] = []
        # We include an average set as we don't want to use a 5-day set to
        # calculate a 7-day average etc. So if an API returns less days than
        # those requested by user we don't use it for average calculations.
        # We could use that data in the average set, but it'd be too much
        # work for now
        data['forecast']['min_values_average_set'] = []
        data['forecast']['max_values_average_set'] = []

        if weather_lookup == 'forecast':
            # reduce yahoo api forecasts
            data['forecast']['max_values'] = WeatherAPI.map_api_data(
                key='high',
                list_of_objects=yahoo_weather.forecasts,
                num_days=date_diff,
                offset=date_diff_offset
            )
            data['forecast']['max_values_average_set'] += data.get('forecast', {}).get('max_values')
            data['forecast']['min_values'] = WeatherAPI.map_api_data(
                key='low', list_of_objects=yahoo_weather.forecasts, num_days=date_diff,
                offset=date_diff_offset
            )
            data['forecast']['min_values_average_set'] = data.get('forecast', {}).get('min_values')

        # Use secondary API's, Yahoo doesn't provide historical data and the
        # forecast is also not great
        for weather_api in form.cleaned_data['weather_apis']:
            if weather_api.slug == 'yahoo-weather':
                continue

            if weather_api.slug == 'weatherstack' and weather_lookup == \
                    'historical':
                weatherstack_data = WeatherAPI.get_weatherstack_results(
                    city=api_city, api_string=weather_lookup, start_date=start_date,
                    end_date=end_date, num_days=date_diff
                )

                if not weatherstack_data:
                    form.add_error(
                        '',
                        ValidationError(
                            "We had trouble receiving the data from the API. Please try again or contact admin"
                        )
                    )
                    short_circuit(form=form)

            if weather_api.slug == 'openweather' and weather_lookup == \
                    'forecast':
                openweather_data = WeatherAPI.get_openweather_results(
                    weather_object=weather_api,
                    city_lat=data['city_info']['lat'],
                    city_lon=data['city_info']['long']
                )
                if openweather_data:
                    # Process, having issues with openweather at the moment
                    openweather_daily = openweather_data.get('daily')
                    openweather_data_max_values = WeatherAPI.map_api_data(
                        list_of_objects=openweather_daily,
                        key=['temp', 'max'],
                        num_days=date_diff + 1,  # OpenWeather returns 8 days
                        offset=date_diff_offset
                    )
                    openweather_data_min_values = WeatherAPI.map_api_data(
                        list_of_objects=openweather_daily,
                        key=['temp', 'min'],
                        num_days=date_diff,  # OpenWeather returns 8 days
                        offset=date_diff_offset
                    )
                    data['forecast']['max_values'] += openweather_data_max_values
                    data['forecast']['min_values'] += openweather_data_min_values

                    data['forecast']['humidity_values'] += \
                        WeatherAPI.map_api_data(
                        list_of_objects=openweather_daily,
                        key='humidity',
                        num_days=date_diff,
                        offset=date_diff_offset
                    )

                    if len(openweather_data_max_values) >= date_diff:
                        data['forecast']['max_values_average_set'] += openweather_data_max_values
                        data['forecast']['min_values_average_set'] += openweather_data_min_values

            # Use Accuweather API as well to determine averages better
            if weather_api.slug == 'accuweather-forecast':
                # Get the city key based on co-ords
                city_key = WeatherAPI.get_accuweather_location_key(
                    lat=data['city_info']['lat'], long=data['city_info']['long']
                )
                if not city_key:
                    continue

                # Accuweather only supports 5 day forecasts
                accuweather_data = WeatherAPI.get_accuweather_results(
                    weather_object=weather_api, city_key=city_key
                )
                if not accuweather_data:
                    continue

                accuweather_data_max_values = WeatherAPI.map_api_data(
                    key=['Temperature', 'Maximum', 'Value'],
                    list_of_objects=accuweather_data.get('DailyForecasts', []),
                    num_days=date_diff,
                    offset=date_diff_offset
                )
                accuweather_data_min_values = WeatherAPI.map_api_data(
                    key=['Temperature', 'Minimum', 'Value'],
                    list_of_objects=accuweather_data.get('DailyForecasts', []),
                    num_days=date_diff,
                    offset=date_diff_offset
                )

                # Process data
                data['forecast']['max_values'] += accuweather_data_max_values
                data['forecast']['min_values'] += accuweather_data_min_values

                if len(accuweather_data_max_values) >= date_diff:
                    data['forecast']['max_values_average_set'] += accuweather_data_max_values
                    data['forecast']['min_values_average_set'] += accuweather_data_min_values
        if data.get('forecast', {}).get('humidity_values'):
            data['forecast']['mean_humidity'] = mean(data['forecast']['humidity_values'])
            data['forecast']['median_humidity'] = median(data['forecast']['humidity_values'])
            data['forecast']['min_humidity'] = min(data['forecast']['humidity_values'])
            data['forecast']['max_humidity'] = max(data['forecast']['humidity_values'])

        data['forecast']['all_temperatures_set'] = data['forecast']['min_values_average_set'] + data['forecast']['max_values_average_set']
        data['forecast']['mean_temperature'] = mean(data['forecast']['all_temperatures_set'])
        data['forecast']['median_temperature'] = median(data['forecast']['all_temperatures_set'])
        data['forecast']['min_temperature'] = min(data['forecast']['min_values'])
        data['forecast']['max_temperature'] = max(data['forecast']['max_values'])
        data['start_date'] = start_date
        data['end_date'] = end_date
        
        weather_history = WeatherAPIRequestRecord()
        weather_history.date = datetime.today()
        weather_history.start_date = start_date
        weather_history.end_date = end_date
        
        weather_history.user_city = form.cleaned_data['city']
        weather_history.api_city = data['city']
        
        weather_history.json_results = data
        
        weather_history.computed_min_temperature = data.get('forecast', {}).get('min_temperature', 0)
        weather_history.computed_max_temperature = data.get('forecast', {}).get('max_temperature', 0)
        weather_history.computed_mean_temperature = data.get('forecast', {}).get('mean_temperature', 0)
        weather_history.computed_median_temperature = data.get('forecast', {}).get('median_temperature', 0)

        weather_history.computed_min_humidity = data.get('forecast', {}).get('min_humidity', 0)
        weather_history.computed_max_humidity = data.get('forecast', {}).get('max_humidity', 0)
        weather_history.computed_mean_humidity = data.get('forecast', {}).get('mean_humidity', 0)
        weather_history.computed_median_humidity = data.get('forecast', {}).get('median_humidity', 0)

        weather_history.save()
        # return results
        return http.JsonResponse(
            data=data,
            status=status.HTTP_200_OK
        )


class WeatherHistoryView(View):
    template_name = 'templates/weather_history.html'

    def get(self, request, *args, **kwargs):
        histories = WeatherAPIRequestRecord.objects.all().order_by('-created_date')
        return render(request, self.template_name, {'histories': histories})