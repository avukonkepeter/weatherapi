import uuid
import urllib
from datetime import timedelta
import json
from functools import reduce


from django.db import models


import requests
from jsonfield import JSONField
from yahoo_weather.weather import YahooWeather


class WeatherAPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(blank=False, null=False, max_length=256)
    url = models.URLField(blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(auto_created=False, blank=True, null=True)
    # Is user accessible API, from homepage ?
    userapi = models.BooleanField(default=False, blank=False, null=False)
    requires_oauth = models.BooleanField(default=False, blank=False, null=False)
    # Most Oauth API implementations will use id and secret convention
    application_id = models.CharField(blank=True, null=True, max_length=256)
    client_id_key = models.CharField(blank=True, null=True, max_length=256)
    client_secret = models.CharField(blank=True, null=True,  max_length=256)

    @staticmethod
    def get_api_data(url, query):
        url_params = urllib.parse.urlencode(query)
        encoded_url = f"{url}?{url_params}"
        api_request = requests.get(encoded_url)
        data = json.loads(api_request.content)
        return data or {}

    @classmethod
    def get_yahoo_results(cls, yahoo_weather_object=None, city=''):
        if not city:
            return None
        # Get data from Yahoo API
        if not yahoo_weather_object:
            yahoo_weather_object = cls.objects.filter(slug='yahoo-weather').first()
        YahooWeatherApi = YahooWeather(
            APP_ID=yahoo_weather_object.application_id,
            api_key=yahoo_weather_object.client_id_key,
            api_secret=yahoo_weather_object.client_secret
        )
        weather = YahooWeatherApi.get_yahoo_weather_by_city(city)
        return weather

    @classmethod
    def get_accuweather_location_key(cls, lat='', long=''):
        if not all([lat, long]):
            return ''
        geoposition_api = cls.objects.get(slug='accuweather-geoposition')
        api_query = {
            'apikey': geoposition_api.client_id_key,
            'q': f"{lat},{long}",
            'toplevel': True
        }
        return cls.get_api_data(
            url=geoposition_api.url, query=api_query
        ).get('Key', None)

    @classmethod
    def get_accuweather_results(cls, weather_object, city_key=''):
        if not city_key:
            return []
        api_query = {
            'apikey': weather_object.client_id_key,
            'details': 'true',
            'metric': 'true'
        }
        api_url = f"{weather_object.url.rstrip('/')}/{city_key}"
        data = cls.get_api_data(api_url, api_query)
        return data

    @classmethod
    def get_openweather_results(cls, weather_object=None, city_lat='', city_lon='',):
        if not city_lat and city_lon:
            return None

        api_query = {
            'appid': weather_object.client_id_key,
            'lat': city_lat,
            'lon': city_lon,
            'exclude': "minutely, hourly",
            'units': 'metric'
        }
        data = cls.get_api_data(weather_object.url, api_query)
        return data

    @classmethod
    def get_weatherstack_results(cls, weather_object=None, city='', api_string='', start_date=None, num_days=0):
        if not city:
            return None
        if not weather_object:
            weather_object = cls.objects.get(slug='weatherstack')

        api_url = weather_object.url.strip('/')
        api_query = {
            'query': city,
            'access_key': weather_object.client_id_key,
        }
        if api_string == 'historical':
            # For historical data we need to pass the dates as semi-colon seperated url string
            historical_dates = [
                start_date + timedelta(days=x) for x in range(num_days + 1)
            ]
            historical_dates = [
                str(dt) for dt in historical_dates
            ]
            api_query['historical_date'] = ';'.join(historical_dates)
            api_query['hourly'] = 24

        if api_string == 'forecast':
            api_query['interval'] = 24
            api_query['forecast_days'] = 7 if num_days <= 7 else 14

        return cls.get_api_data(api_url, api_query)

    @classmethod
    def compute_average(cls, temperatures=[]):
        pass

    @classmethod
    def map_api_data(cls, key='', list_of_objects=[], num_days=0, offset=0):
        if not key or not list_of_objects:
            return []
        # If type of key is list, we assume this is a recursive get operation
        if type(key) == list:
            data = []

            for element in list_of_objects:
                value = reduce(
                    lambda nested_dictionary, current_key: nested_dictionary.get(current_key, {}),
                    key,
                    element
                )
                data.append(value)
            return data[offset:num_days]

        def item_lookup(item, key):
            if type(item) == dict:
                return item.get(key)
            else:
                return item.__dict__.get(key)

        return [
            item_lookup(item, key)
            for item in list_of_objects
            if item_lookup(item, key)
        ][offset:num_days]

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"{self.name} - {self.url}"


class WeatherAPIRequestRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_date = models.DateTimeField(auto_now_add=True)
    date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=False, blank=False)
    start_date = models.DateField(null=False, blank=False)
    api = models.ForeignKey(WeatherAPI, blank=True, null=True,on_delete=models.DO_NOTHING)
    user_city = models.CharField(null=False, blank=False, max_length=256)
    api_city = models.CharField(null=False, blank=False, max_length=256)
    json_results = JSONField(null=True, blank=True, default=list)
    computed_min_temperature = models.FloatField(null=True, blank=True)
    computed_max_temperature = models.FloatField(null=True, blank=True)
    computed_min_humidity = models.FloatField(null=True, blank=True)
    computed_max_humidity = models.FloatField(null=True, blank=True)
    computed_mean_humidity = models.FloatField(null=True, blank=True)
    computed_mean_temperature = models.FloatField(null=True, blank=True)
    computed_median_humidity = models.FloatField(null=True, blank=True)
    computed_median_temperature = models.FloatField(null=True, blank=True)

    @property
    def date_range(self):
        return f"{self.start_date} to {self.end_date}"