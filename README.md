# Team Me0w

<img src="images/meow-logo.png" width="400"></img>

Every day public transit networks (PTNs) play a critical role in the lives of millions of people. Because of their importance, one developing trend is the use of numerical graph methods in order to examine different aspects of a PTN, such as equity, transit frequency, and vulnerability. Our team hopes to help public transit planners by providing a free, user-friendly web application for analyzing PTNs based on publicly available GTFS data. Besides providing users with the ability to build aggregate networks from multiple transit types (e.g., combining Caltrain, BART, and Muni), Transitcat also makes it easy to visualize them and understand real-world usability through the use of isochrone maps. We're just three cat lovers hoping to improve the world, one public transit stop at a time.


# Getting Transitcat Running

You'll need to follow these steps once to set up the project:

1. Download a local copy of this entire repository. Be sure to follow the [instructions](https://github.com/StanfordCS194/Me0w/tree/master/src) for setting up your directory structure.
2. Install [Postgres](https://wiki.postgresql.org/wiki/Detailed_installation_guides) on your machine. An easy way to do this is using Homebrew with the command `brew install postgres`.
3. In your Terminal, run the commmand `postgres -D /usr/local/var/postgres` to start Postgres.
4. In a new Terminal tab/window, open the Postgres prompt by typing `psql`. Next create your user using the username and password of your choice by typing `CREATE USER sample_user WITH PASSWORD 'sample_password';`. Finish by typing `CREATE DATABASE transitcat WITH OWNER sample_user;`, which creates a database called `transitcat` and gives your user access. Exit by typing `/q`.
5. Update your [`settings.py`](https://github.com/aaronaquino/transitcat/blob/master/src/DjangoSite/DjangoSite/settings.py) file so that Transitcat can find your database. Scroll down to the section that says:
```
DATABASES = {
    "default": {
    "ENGINE": "django.db.backends.postgresql_psycopg2",
    ...
```
Replace `"YOUR_USERNAME_HERE"` and `"YOUR_PASSWORD_HERE"` with the values you assigned to your Postgres user.

6. Navigate to the directory containing [`manage.py`](https://github.com/aaronaquino/transitcat/blob/master/src/DjangoSite/manage.py) and run the following command: `python manage.py migrate`.
7. Apply for free, personal API keys for [Yelp](https://www.yelp.com/developers/documentation/v3/authentication) and [Google Maps](https://developers.google.com/maps/documentation/javascript/get-api-key).
  * Add your Yelp API key to [`yelp.py`](https://github.com/aaronaquino/transitcat/blob/master/src/DjangoSite/snapData/Backend/yelp.py). Do so by scrolling down to the section that says:
```
# TODO: Uncomment the line below and add your Yelp API key.
# HEADERS={"Authorization":"Bearer YOUR_KEY_HERE"}
```
  * Add your Google Maps API key to [`mapStop.html`](https://github.com/aaronaquino/transitcat/blob/master/src/DjangoSite/snapData/templates/snapData/mapStop.html) and [`mapTest.html`](https://github.com/aaronaquino/transitcat/blob/master/src/DjangoSite/snapData/templates/snapData/mapTest.html). Do so by scrolling down to the section that says:
```
<script async defer
src="https://maps.googleapis.com/maps/api/js?key=YOUR_API_KEY_HERE&callback=initMap">
</script>
```

---

Now every time you want to run Transitcat, simply do the following:

1. In your Terminal, run the commmand `postgres -D /usr/local/var/postgres`.
2. In a new Terminal tab/window, navigate to the directory containing [`manage.py`](https://github.com/StanfordCS194/Me0w/blob/master/src/DjangoSite/manage.py) and run the following command: `python manage.py runserver`.
3. Point your web browser to [http://127.0.0.1:8000/snapData/](http://127.0.0.1:8000/snapData/), and you're off!


# Team Members
Member | Photograph
--- | ---
Aaron Aquino (aaron33) | <img src="https://aaronaquino.github.io/assets/profile_old.png" width="150" alt="Aaron Aquino"> 
Tracey Lin (traceyl) | <img src="https://scontent-sjc3-1.xx.fbcdn.net/v/t31.0-8/15585359_1201367849919117_7963034359442281739_o.jpg?_nc_cat=0&oh=3d93468956ab9e74964ca3f5af01f4bf&oe=5BA5816D" width="150" alt="Tracey Lin"> 
Erik Raucher (eraucher) | <img src="https://scontent.fsea1-1.fna.fbcdn.net/v/t1.0-9/1604902_795937910421737_1690745874_n.jpg?_nc_cat=0&oh=817067c09208ebe1ad6820c9e6c2c4bc&oe=5B74B711" width="150" alt="Erik Raucher">
