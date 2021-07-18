# WEATHER API LOOKUP

Looks up weather data from multiple API's, aggregates it and returns it to the user either via a front-end or as a JSON response.

### Installation:

- Create a virtual environment using your preferred environment manager (pyenv, virtualenvwrapper etc.) and activate it.

###### Run:

`chmod +x ./install.sh`

`./install.sh`

- Run the migrations, the app will use the default sqlite database:

`python manage.py migrate`

- Run the server and navigate to 'http://127.0.0.1:8000'

###### API Lookup:

`/api/locations/{city}/?days={number_of_days}`

Where:

- _city_ is any city around the world as a string
- _number_of_days_ is an integer with the number of days results to aggregate.
- *Optional: query param _full=True_ will return a more comprehensive dataset with information such as humidity included and other info about the city being searched.

###### Front-End:

Navigate to http://127.0.0.1:8000 to view the front-end

Enter the desired 'city', 'start_date' and 'end_date' for your weather lookup and choose the API's you would like to search, aggregated data will be returned to you via the front-end

###### Tests:

`python manage.py test`

###### History:

Navigate to 'http://127.0.0.1:8000/weatherhistory' to view the request history.
