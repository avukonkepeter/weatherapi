from datetime import datetime, timedelta, date
from statistics import median, mean


from django.shortcuts import render
from django import http
from django.views import View
from django.forms import ValidationError
from django.conf import settings


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


class WeatherView(APIView, APIViewToViewsetMixin):
    """
    Accept a POST request with 'City' and 'Period' information.

    Return json response with 'min', 'max', 'average', 'median' temperature
    as received from the weather API
    """

    short_circuit = lambda instance, form, request: render(request, 'index.html', {'form': form})
    http_short_circuit = lambda instance, error_dict: http.JsonResponse(data={
        'has_error': True, 'errors': list(error_dict.values())})
    form_class = LandingPageForm
    form = None

    def get(self, request, city='', full=False):
        city = city.strip()

        if not city:
            return http.JsonResponse(
                data={'message': 'Please enter a valid city',},
                status=status.HTTP_400_BAD_REQUEST
            )

        query_params = request.GET
        days = settings.DEFAULT_QUERY_DURATION_DAYS
        if 'days' in query_params:
            days = int(query_params.get('days'))
        if 'full' in query_params:
            full = True

        start_date = datetime.today()
        end_date = start_date + timedelta(days=days)
        self.form = self.form_class(
            data={
                'city': city, 'start_date': start_date, 'end_date': end_date,
                'weather_apis': WeatherAPI.objects.filter(userapi=True).all()
            }
        )
        self.form.is_valid()
        circuit = self.check_circuits(start_date=start_date, end_date=end_date, weather_lookup='forecast')
        if circuit: return circuit

        data = self.get_api_data(days=days, city=city, weather_lookup='forecast')

        if not full:
            return_data = {
                'maximum': data.get('forecast', {}).get('max_temperature'),
                'minimum': data.get('forecast', {}).get('min_temperature'),
                'average': data.get('forecast', {}).get('mean_temperature'),
                'median': data.get('forecast', {}).get('median_temperature'),
            }
            data = return_data

        return http.JsonResponse(
            data=data,
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):

        # TODO: Support end_date < start_date, reverse dates, do request and
        #  return results in reverse

        data = request.data
        self.form = LandingPageForm(data=data)
        # Standard django validation
        if not self.form.is_valid():
            return http.JsonResponse(
                data={
                    'has_error': True, 'error': self.form.non_field_errors()
                },
            )
            # return render(request, 'index.html', {'form': self.form})

        # Determine date is in correct format
        start_date = self.form.cleaned_data['start_date']
        end_date = self.form.cleaned_data['end_date']
        # Determine whether to forecast or get historical data
        weather_lookup = 'historical' if start_date < date.today() else 'forecast'
        circuit = self.check_circuits(start_date=start_date, end_date=end_date, weather_lookup=weather_lookup)
        if circuit:
            return circuit

        date_diff = end_date - start_date
        # For some reason yyyy/mm/3 - yyyy/mm/1 would give you 2 as answer,
        # but if you count in days it would be 3, jitter by 1
        date_diff = date_diff.days + 1
        # Diff offset used to return days relative to today (future)
        date_diff_offset = start_date - date.today()
        date_diff_offset = date_diff_offset.days

        city = self.form.cleaned_data['city']

        data = self.get_api_data(
            request=request, days=date_diff, city=city,
            weather_lookup=weather_lookup, days_offset=date_diff_offset,
            start_date=start_date, end_date=end_date
        )

        if type(data) != dict:
            return data

        self.store_weather_api_request_record(data=data, start_date=start_date, end_date=end_date)

        # return results
        return http.JsonResponse(
            data=data,
            status=status.HTTP_200_OK
        )

    def check_circuits(self, request=None, start_date=None, end_date=None, weather_lookup=''):
        if end_date < start_date:
            self.form.add_error(
                None,
                ValidationError(
                    "Please Ensure that the 'start_date' is greater than the 'end_date'"
                )
            )

        if end_date - start_date > timedelta(days=settings.MAX_QUERY_DURATION_DAYS):
            self.form.add_error(
                None,
                ValidationError(
                    "App currently doesn't support weather forecasts for "
                    "more than 10 days"
                )
            )

        if weather_lookup == 'historical':
            # temporarily disable historical functionality till further notice
            self.form.add_error(
                'start_date',
                ValidationError(
                    "App will not be supporting historical lookups due to "
                    "API constraints. Historical weather lookups will return "
                    "an error until further notice"
                )
            )

        if end_date > start_date + timedelta(days=settings.MAX_QUERY_DURATION_DAYS):
            self.form.add_error(
                '',
                ValidationError(
                    f"App currently doesn't support weather forecasts for "
                    f"more than {settings.MAX_QUERY_DURATION_DAYS} days into the future"
                )
            )

        if self.form.errors:
            return self.http_short_circuit(self.form.errors)

    def get_api_data(self, request=None, days=0, weather_lookup='', city='',
                     days_offset=0, start_date='', end_date=''):
        data = {'city_info': {}, 'forecast': {}}
        data['user_city'] = city
        data['forecast']['min_values'] = []
        data['forecast']['max_values'] = []

        data['forecast']['humidity_values'] = []
        data['forecast']['humidity_values_average_set'] = []
        # We include an average set as we don't want to use a 5-day set to
        # calculate a 7-day average etc. So if an API returns less days than
        # those requested by user we don't use it for average calculations.
        # We could use that data in the average set, but it'd be too much
        # work for now
        data['forecast']['min_values_average_set'] = []
        data['forecast']['max_values_average_set'] = []

        if self.form and self.form.cleaned_data:
            form_api_slugs = self.form.cleaned_data['weather_apis']
        else:
           form_api_slugs = WeatherAPI.objects.filter(userapi=True).all()

        if not days:
            days = settings.DEFAULT_QUERY_DURATION_DAYS

        weatherapi = self.get_weatherapi_data(
            city=city, days=days, weather_lookup=weather_lookup
        )

        if weatherapi.get('error', '') or not weatherapi:
            self.form.add_error(
                None,
                ValidationError(
                    f'We could not find a match for the city you entered. '
                    f'Please make sure you\'ve entered the city name correctly. '
                    f'Code: {weatherapi.get("error", {}).get("code")}; '
                    f'Message: {weatherapi.get("error", {}).get("message")}'
                )
            )
            return self.http_short_circuit(self.form.errors)

        # We have a city
        api_city = weatherapi.get('location', {}).get('name', '')
        # City info
        data['city'] = api_city
        # Check if user entered city exactly as what we returned: Indicate
        # this is a fuzzy result
        data['cities_match'] = api_city.strip().lower() == city.strip().lower()
        data['city_info'].update({
            k: v for k, v in weatherapi.get('location', {}).items()
            if k not in ['name', ]
        })
        city_latitude = data.get('city_info', {}).get('lat', '')
        city_longitude = data.get('city_info', {}).get('lon', '')

        # Get Accuweather data for this location as well.
        accuweather_data = self.get_accuweatherapi_data(
            city=data['city'], days=days, days_offset=days_offset
        )
        if accuweather_data:
            data['city_info']['lat'] = WeatherAPI.map_api_data(
                key=['GeoPosition', 'Latitude'],
                list_of_objects=[accuweather_data],
                num_days=days, offset=days_offset
            )[0]
            data['city_info']['lon'] = WeatherAPI.map_api_data(
                key=['GeoPosition', 'Longitude'],
                list_of_objects=[accuweather_data],
                num_days=days, offset=days_offset
            )[0]

            city_longitude = data.get('city_info', {}).get(
                'lon', data.get('city_info', {}).get('long', {})
            )

        # Get list of forecasts
        api_forecasts_list = weatherapi.get('forecast', {}).get('forecastday', [])

        if weather_lookup == 'forecast' and days <= len(api_forecasts_list):
            # reduce openweather api forecasts
            data['forecast']['max_values'] = WeatherAPI.map_api_data(
                key=['day', 'maxtemp_c'], list_of_objects=api_forecasts_list,
                num_days=days, offset=days_offset
            )
            data['forecast']['max_values_average_set'] += data.get('forecast', {}).get('max_values')

            data['forecast']['min_values'] = WeatherAPI.map_api_data(
                key=['day', 'mintemp_c'], list_of_objects=api_forecasts_list,
                num_days=days, offset=days_offset
            )
            data['forecast']['min_values_average_set'] += data.get('forecast', {}).get('min_values')

            # Humidity
            data['forecast']['humidity_values_average_set'] += WeatherAPI.map_api_data(
                key=['day', 'avghumidity'],
                list_of_objects=api_forecasts_list,
                num_days=days,
                offset=days_offset
            )

        # Use secondary API's, Yahoo doesn't provide historical data and the
        # forecast is also not great
        for weather_api in form_api_slugs:

            if weather_api.slug == 'openweather' and weather_lookup == 'forecast':

                openweather_data = self.get_openweather_data(
                    weather_api=weather_api, city_latitude=city_latitude,
                    city_longitude=city_longitude
                )

                if not openweather_data:
                    continue

                # Process, having issues with openweather at the moment
                openweather_daily = openweather_data.get('daily')

                if len(openweather_daily) < days:
                    # Prevent muddying of data by shorter datasets
                    continue

                openweather_data_max_values = WeatherAPI.map_api_data(
                    list_of_objects=openweather_daily,
                    key=['temp', 'max'],
                    num_days=days + 1,  # OpenWeather returns 8 days
                    offset=days_offset
                )
                openweather_data_min_values = WeatherAPI.map_api_data(
                    list_of_objects=openweather_daily,
                    key=['temp', 'min'],
                    num_days=days,  # OpenWeather returns 8 days
                    offset=days_offset
                )
                data['forecast']['max_values'] += openweather_data_max_values
                data['forecast']['min_values'] += openweather_data_min_values

                humidity_values = WeatherAPI.map_api_data(
                    list_of_objects=openweather_daily, key='humidity',
                    num_days=days, offset=days_offset
                )

                data['forecast']['humidity_values'] = humidity_values
                data['forecast']['humidity_values_average_set'] += humidity_values

                # OpenWeather results take precedence for temperature
                # readings (more comprehensive data)
                data['forecast']['max_values_average_set'] = openweather_data_max_values
                data['forecast']['min_values_average_set'] = openweather_data_min_values

            # Use Accuweather API as well to determine averages better
            if weather_api.slug == 'accuweather-forecast' and accuweather_data:
                # Get the city key based on co-ords
                city_key = accuweather_data.get('Key')
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
                    num_days=days,
                    offset=days_offset
                )
                accuweather_data_min_values = WeatherAPI.map_api_data(
                    key=['Temperature', 'Minimum', 'Value'],
                    list_of_objects=accuweather_data.get('DailyForecasts', []),
                    num_days=days,
                    offset=days_offset
                )

                if not 'openweather' in form_api_slugs and len(accuweather_data_max_values) <= days:
                    # Process data
                    data['forecast']['max_values'] += accuweather_data_max_values
                    data['forecast']['min_values'] += accuweather_data_min_values

                if len(accuweather_data_max_values) >= days:
                    data['forecast']['max_values_average_set'] += accuweather_data_max_values
                    data['forecast']['min_values_average_set'] += accuweather_data_min_values

        data = self.calculate_data_averages(data=data)
        data['start_date'] = start_date
        data['end_date'] = end_date

        return data

    @staticmethod
    def calculate_data_averages(data=None):
        if data is None:
            data = {}

        if data.get('forecast', {}).get('humidity_values'):
            data['forecast']['mean_humidity'] = mean(data['forecast']['humidity_values_average_set'])
            data['forecast']['median_humidity'] = median(data['forecast']['humidity_values_average_set'])
            data['forecast']['min_humidity'] = min(data['forecast']['humidity_values_average_set'])
            data['forecast']['max_humidity'] = max(data['forecast']['humidity_values_average_set'])

        data['forecast']['all_temperatures_set'] = data['forecast']['min_values_average_set'] + data['forecast']['max_values_average_set']
        data['forecast']['mean_temperature'] = mean(data['forecast']['all_temperatures_set'])
        data['forecast']['median_temperature'] = median(data['forecast']['all_temperatures_set'])
        data['forecast']['min_temperature'] = min(data['forecast']['min_values'])
        data['forecast']['max_temperature'] = max(data['forecast']['max_values'])

        return data

    def get_weatherapi_data(self, city='', days=0, weather_lookup=''):
        # Get weatherapi data
        weatherapi_instance = WeatherAPI.objects.get(slug='weatherapi')
        url = f"{weatherapi_instance.url}/forecast.json"
        query = {
            'q': city, 'key': weatherapi_instance.client_id_key
        }
        if weather_lookup == 'forecast':
            query['days'] = days
        weatherapi = WeatherAPI.get_api_data(url=url, query=query)

        return weatherapi

    def get_accuweatherapi_data(self, city='', days=0, days_offset=0):
        accuweather_instance = WeatherAPI.objects.get(slug='accuweather-cities')
        accuweather_query = {
            'q': city, 'apikey': accuweather_instance.client_id_key,
            'alias': 'Never', 'limit': 0
        }
        accuweather_instance_data = WeatherAPI.get_api_data(accuweather_instance.url, accuweather_query)
        top_accuweather_result = []
        if accuweather_instance_data and type(accuweather_instance_data) == list:
            top_accuweather_result = accuweather_instance_data[0]

        return top_accuweather_result

    def get_openweather_data(self, weather_api=None, city_latitude='', city_longitude='', days=0, days_offset=0):
        openweather_data = WeatherAPI.get_openweather_results(
            weather_object=weather_api,
            city_lat=f'{city_latitude}',
            city_lon=f'{city_longitude}'
        )
        return openweather_data

    def store_weather_api_request_record(self, data=None, start_date='', end_date=''):
        if not data:
            return {}

        weather_history = WeatherAPIRequestRecord()
        weather_history.date = datetime.today()
        weather_history.start_date = start_date
        weather_history.end_date = end_date

        weather_history.user_city = data.get('user_city', '')
        weather_history.api_city = data.get('city', '')

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

        return weather_history


class WeatherHistoryView(View):
    template_name = 'templates/weather_history.html'

    def get(self, request, *args, **kwargs):
        histories = WeatherAPIRequestRecord.objects.all().order_by('-created_date')
        return render(request, self.template_name, {'histories': histories})
