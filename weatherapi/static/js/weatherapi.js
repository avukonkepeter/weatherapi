$(window).on('load', (e) => {
   $("#cityHelpInline").toggle();
   $(".cityInfoDisplay, .temperatureDisplay, .humidityDisplay, .graphDisplay").toggle();
});

$(document).ready((e) => {
    $('#weatherViewForm').on('submit', (e) =>{$("#cityHelpInline").hide();
   $(".cityInfoDisplay, .temperatureDisplay, .humidityDisplay, .graphDisplay").hide();
        e.preventDefault();
        let form = e.currentTarget;
        let formData = new FormData(form);
        // Do Ajax Check, if no value, then display error || fuzzy logic
        $.ajax({
            url: form.action,
            data: formData,
            cache: false,
            processData: false,
            contentType: false,
            type: 'POST',
            success: (data) => {
                // We got positive data back from the user, continue to display data
                $("#" + form.id).trigger('reset');

                let cityName = maxTemperature = maxHumidity = minTemperature = minHumidity = meanTemperature = meanHumidity = medianHumidity = medianTemperature = startDate = endDate = celcius = ''
                let cityMatches = true;

                if (!$.isEmptyObject(data) && typeof(data) === 'object'){
                    let citiesMatch = data['cities_match'];
                    if (!citiesMatch){
                        $("#fuzzyInfo").text(
                            'We have shown information for "' + data['city'] + '". This is the closest match we could find to the city you entered'
                        );
                    } else {
                        $("#fuzzyInfo").text("");
                    }

                    // Temperature Values
                    maxTemperature = Math.round(data['forecast']['max_temperature']);
                    minTemperature = Math.round(data['forecast']['min_temperature']);
                    meanTemperature = Math.round(data['forecast']['mean_temperature']);
                    medianTemperature = Math.round(data['forecast']['median_temperature']);

                    // Humidity Values
                    maxHumidity = Math.round(data['forecast']['max_humidity']);
                    minHumidity = Math.round(data['forecast']['min_humidity']);
                    meanHumidity = Math.round(data['forecast']['mean_humidity']);
                    medianHumidity = Math.round(data['forecast']['median_humidity']);

                    // City Data
                    cityMatches = data['cities_match'];
                    cityName = data['city'];
                    startDate = data['start_date'];
                    endDate = data['end_date'];
                    celcius = String.fromCharCode(8451);
                }


                $(".cityInfoSpan").text(cityName);
                $(".cityDateSpan").text(
                    startDate + " - " + endDate
                );

                $("#maxTemperatureCard").text(maxTemperature + celcius);
                $("#minTemperatureCard").text(minTemperature + celcius);
                $("#meanTemperatureCard").text(meanTemperature + celcius);
                $("#medianTemperatureCard").text(medianTemperature + celcius);

                $("#maxHumidityCard").text(maxHumidity + "%");
                $("#minHumidityCard").text(minHumidity + "%");
                $("#meanHumidityCard").text(meanHumidity + "%");
                $("#medianHumidityCard").text(medianHumidity + "%");

                $(".cityInfoDisplay, .temperatureDisplay, .humidityDisplay, .graphDisplay").toggle();
            },
            error: error => {
                // Something wrong with the city, display to user
                console.log(error);
            }
        });
    });
});