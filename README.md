# Garmin Activities Map

Tool to render Garmin activities on a map. It downloads activities from Garmin Connect, stores them locally, generates an HTML file
with all the activities shown on an interactive map and optionally uploads it to an FTP site. It gives you an easy-to-understand overview of
where you were, which paths you visited and which are still waiting for you.

It is a tool not an application. A couple of steps are needed to make it work and some code adjustments may be required to match
your needs.

It should be useful primarily for people using Garmin Connect as the main repository of their activities. If you use Strava, I would recommend
to look into [StatsHunters](https://www.statshunters.com), which is a more mature and feature-rich application.


## What it produces

Example with a light background map:

![White map](images/white.png)

Example with a dark background map:

![Black map](images/black.png)

Hovering over an activity highlights it. Clicking an activity opens a popup with basic information about the activity and a link to Garmin
Connect:

![Activity popup](images/activity-popup.png)

Map controls allow for selection of background map, selection of activity categories to show and for zooming in/out:

![Map controls](images/controls.png)


## How to get it working

* install Python 3
* get python dependencies from requirements.txt
* only if you want to upload resulting map to an FTP site
  * copy the [ftp] section from config-default.toml to config-local.toml and populate it with your personal values
  * first put your password in plain-text there
  * run the tool while setting all the processors to OFF and setting utility-mode to ENCRYPT_FTP_PASSWORD
  * replace password in the config with the printed encrypted version
  * switch back all the processors to ON
* only if you want to use Mapy.cz map tiles (useful mostly for tourist paths in Central Europe region):
  * go to https://developer.mapy.cz/en/rest-api-mapy-cz/api-key/
  * generate your own API key
  * store the key in config-local.toml in [map-tiles] section as mapy-cz-api-key
* on the first run you will be asked for your Garmin credentials. It will then generate an authentication token which will be persisted 
locally in .auth directory and will work for a year


## How to use it

* Adjust mode values in config-local.toml to reflect what you want to do
* Run activities-map.py
* Open the output `data/activities_map.html` or from your FTP site in your browser
* Next time only new activities will be downloaded and whole map will be regenerated


* If you need to customize behavior of the tool start by understanding config-default.toml and take it from there


## How it works

The tool is broken down into a couple of files which represent sort of isolated functionality.

* activities-map.py - the main file, the central piece which controls the flow and invokes other files
* downloader.py - downloads data from Garmin Connect, reprocesses GPS coordinates of activities
* storage.py - manages local storage of activities data
* mapgenerator.py - creates a map and puts activities on it
* minifier.py - reduces size of the map (code created by mapgenerator is repetitive and verbose)
* ftpuploader.py - uploads the map to an FTP site

There are two configuration files:
* config-default.toml - do not edit, contains default values and explanations of all the properties
* config-local.toml - put your personal config overrides here. This file is not under version control

See comments in individual files for more details.

Communication with Garmin Connect is based on [Python: Garmin Connect](https://github.com/cyberjunky/python-garminconnect) library.
Map generation is done via the [Folium](https://python-visualization.github.io/folium/latest/index.html) library, which creates code based
on the [Leaflet JS](https://leafletjs.com) library.


## Links

* [Python: Garmin Connect](https://github.com/cyberjunky/python-garminconnect) - use Garmin Connect REST API from Python
* [Garth](https://github.com/matin/garth) - lower level library for Garmin Connect API
* [Folium](https://python-visualization.github.io/folium/latest/index.html) - map generator for Python
* [Leaflet JS](https://leafletjs.com) - JavaScript library for maps
* https://www.fitfileviewer.com - web FIT viewer
* https://gpx.studio - web GPX viewer


* related projects:
  * https://github.com/tcgoetz/GarminDB - local database with Garmin activities
  * https://github.com/pe-st/garmin-connect-export
  * https://github.com/danmarg/export_garmin
  * [StatsHunters](https://www.statshunters.com) - application serving similar purpose but for Strava
* working with FIT files:
  * https://fitdecode.readthedocs.io/en/latest/index.html
  * https://github.com/polyvertex/fitdecode
* how to visualize activities:
  * https://medium.com/@azholud/analysis-and-visualization-of-activities-from-garmin-connect-b3e021c62472
  * https://medium.com/@vinodvidhole/interesting-heatmaps-using-python-folium-ee41b118a996


## Ideas, todos

* add command line parameters to override config to allow for scheduling of automatic run
* resolve Closure warnings
* find all activities in a selection rectangle
* put it online - hosting with python and storage
