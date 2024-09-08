Note
- currently requires custom fork of python-garminconnect to make it work
  - https://github.com/MareenCZE/python-garminconnect
  - check it out to your environment and run: "pip install -e ."

Links
 - this code is based on https://github.com/cyberjunky/python-garminconnect
 - another related projects which creates a local DB from activities https://github.com/tcgoetz/GarminDB
 - both are based on more low-level https://github.com/matin/garth
 - library for parsing of FIT files https://fitdecode.readthedocs.io/en/latest/index.html
 - web FIT viewer https://www.fitfileviewer.com
 - web GPX viewer https://gpx.studio

 - articles about how to visualize activities
    - how to create heat map https://medium.com/@azholud/analysis-and-visualization-of-activities-from-garmin-connect-b3e021c62472
    - https://medium.com/@vinodvidhole/interesting-heatmaps-using-python-folium-ee41b118a996
 - Python library to generate heat map https://python-visualization.github.io/folium/latest/index.html
    - uses JS library for maps https://leafletjs.com
 - https://github.com/pe-st/garmin-connect-export
 - https://github.com/danmarg/export_garmin
 - https://github.com/tcgoetz/GarminDB
 - https://github.com/polyvertex/fitdecode

TODO
- reduce size of javascript code. Generated code is very repetitive
    - try https://github.com/google/closure-compiler
    - see https://andrewpwheeler.com/2024/08/04/reducing-folium-map-sizes/
- highlight selected activity (commented out for now, increases size)
- put it online - hosting with python and storage, lambdas?
- update readme
- filtering by year, lazy loading
