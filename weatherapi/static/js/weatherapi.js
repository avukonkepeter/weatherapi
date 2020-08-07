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

                let citiesMatch = data['cities_match'];
                if (!citiesMatch){
                    $("#fuzzyInfo").text(
                        'We have shown information for "' + data['city'] + '". This is the closest match we could find to the city you entered'
                    );
                } else {
                    $("#fuzzyInfo").text("");
                }

                // Temperature Values
                let maxTemperature = Math.round(data['forecast']['max_temperature']);
                let minTemperature = Math.round(data['forecast']['min_temperature']);
                let meanTemperature = Math.round(data['forecast']['mean_temperature']);
                let medianTemperature = Math.round(data['forecast']['median_temperature']);

                // Humidity Values
                let maxHumidity = Math.round(data['forecast']['max_humidity']);
                let minHumidity = Math.round(data['forecast']['min_humidity']);
                let meanHumidity = Math.round(data['forecast']['mean_humidity']);
                let medianHumidity = Math.round(data['forecast']['median_humidity']);

                // City Data
                let cityMatches = data['cities_match'];
                let cityName = data['city'];
                let startDate = data['start_date'];
                let endDate = data['end_date'];
                let celcius = String.fromCharCode(8451);

                $(".cityInfoSpan").text(cityName);
                $(".cityDateSpan").text(
                    startDate + " - " + endDate
                );

                $("#maxTemperatureCard").text(maxTemperature + celcius);
                $("#minTemperatureCard").text(minTemperature + celcius);
                $("#meanTemperatureCard").text(meanTemperature + celcius);
                $("#medianTemperatureCard").text(medianTemperature + celcius);
                if (data['forecast']['humidity_values'].length > 0){
                    $("#maxHumidityCard").text(maxHumidity + "%");
                    $("#minHumidityCard").text(minHumidity + "%");
                    $("#meanHumidityCard").text(meanHumidity + "%");
                    $("#medianHumidityCard").text(medianHumidity + "%");
                }

                $(".cityInfoDisplay, .temperatureDisplay, .humidityDisplay, .graphDisplay").toggle();
            },
            error: error => {
                // Something wrong with the city, display to user
                console.log(error)
            }
        });
    });
});