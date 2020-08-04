from django.shortcuts import render
from django import http
from django.views import View

from rest_framework.views import APIView
from rest_framework import status


from weatherapi.forms import LandingPageForm


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


class WeatherHistoryView(View):
    pass