from django.db import models


from jsonfield import JSONField


class WeatherAPI(models.Model):
    name = models.CharField(blank=False, null=False, max_length=256)
    url = models.URLField(blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(auto_created=False, blank=True, null=True)
    # Is user accessible API, from homepage ?
    userapi = models.BooleanField(default=False, blank=False, null=False)
    # token = models.CharField(blank=True, null=True, max_length=256)
    # Most Oauth API implementations will use id and secret convention
    client_id_key = models.CharField(blank=True, null=True, max_length=256)
    client_secret = models.CharField(blank=True, null=True,  max_length=256)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return f"{self.name} - {self.url}"


class WeatherAPIRequestRecord(models.Model):
    date = models.DateField(null=False, blank=False)
    time = models.TimeField(null=False, blank=False)
    api = models.ForeignKey(WeatherAPI, on_delete=models.DO_NOTHING)
    city = models.CharField(null=False, blank=False, max_length=256)
    json_results = JSONField(null=True, blank=True, default=list)
    computed_median = models.FloatField(null=True, blank=True)
    computed_min_temperature = models.FloatField(null=True, blank=True)
    computed_max_temperature = models.FloatField(null=True, blank=True)
    computed_min_humidity = models.FloatField(null=True, blank=True)
    computed_max_humidity = models.FloatField(null=True, blank=True)
    computed_average_humidity = models.FloatField(null=True, blank=True)
    computed_average_temperature = models.FloatField(null=True, blank=True)
    computed_median_humidity = models.FloatField(null=True, blank=True)
    computed_median_temperature = models.FloatField(null=True, blank=True)
