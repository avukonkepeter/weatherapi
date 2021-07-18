from random import choice as random_choice


from django.urls import reverse
from django.conf import settings


from rest_framework.test import APITestCase


cities_choices = [
    'Tokyo', 'Delhi', 'Shanghai', 'Sao Paulo', 'Mexico City', 'Dhaka',
    'Cairo', 'Beijing', 'Mumbai', 'Osaka', 'Karachi', 'Chongqing',
    'Istanbul', 'Buenos Aires', 'Kolkata', 'Kinshasa', 'Lagos', 'Manila',
    'Tianjin', 'Guangzhou'
]


class WeatherAPITestGET(APITestCase):
    fixtures = ['weatherapis.json']

    def setUp(self) -> None:
        self.city = random_choice(cities_choices)
        self.url = reverse('weatherview-get', kwargs={'city': self.city})
        self.num_days = settings.DEFAULT_QUERY_DURATION_DAYS
        self.weather_api_json_keys = [
            'min_humidity', 'max_humidity', 'min_temperature',
            'max_temperature', 'mean_temperature', 'median_temperature',
            'mean_humidity', 'median_humidity'
        ]
        self.yoyo_keys = [
            'maximum', 'minimum', 'average', 'median'
        ]

    def test_incorrect_api_url(self):
        url = '/api/locations'
        r = self.client.get(url, format='json')
        self.assertEqual(r.status_code, 404)

    def test_incorrect_parameters(self):
        url = reverse('weatherview-get', kwargs={'city': " "})
        url = f'{url}?full=True'
        r = self.client.get(url, format='json')
        self.assertIn(r.status_code, [400, 404])
        data = r.json()
        self.assertTrue('message' in data)
        self.assertContains(r, 'enter a valid city', status_code=400)

    def test_get_with_no_days(self):
        days = 0
        url = reverse('weatherview-get', kwargs={'city': self.city})
        url = f"{url}?days={days}&full=True"
        r = self.client.get(url, format='json')
        data = r.json()
        forecast_data = data.get('forecast', {})
        self.assertEqual(r.status_code, 200)
        for key in self.weather_api_json_keys:
            self.assertTrue(key in forecast_data)

    def test_get_too_many_days(self):
        days = settings.MAX_QUERY_DURATION_DAYS * 2
        url = reverse('weatherview-get', kwargs={'city': self.city})
        url = f"{url}?days={days}&full=True"
        r = self.client.get(url, format='json')
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue('errors' in data)
        self.assertTrue(type(data.get('errors') == list))

    def test_get_correct_parameters_full(self):
        url = reverse('weatherview-get', kwargs={'city': self.city})
        url = f"{url}?days={self.num_days}&full=True"
        r = self.client.get(url, format='json')
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(data.get('user_city') == self.city)
        forecast_data = data.get('forecast', {})
        for key in self.weather_api_json_keys:
            self.assertTrue(key in forecast_data)

    def test_get_correct_parameters_yoyo_format(self):
        url = reverse('weatherview-get', kwargs={'city': self.city})
        url = f"{url}?days={self.num_days}"
        r = self.client.get(url, format='json')
        data = r.json()
        self.assertEqual(r.status_code, 200)
        for key in self.yoyo_keys:
            self.assertTrue(key in data)
