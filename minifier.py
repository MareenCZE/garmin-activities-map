#!/usr/bin/env python3
import os.path
import re
import subprocess

from common import logger


# This part of code is not required for functionality, it only helps to reduce size of the output.
# At the same time it is the least robust part of the code and has high potential to break in the future.
# It also requires you to have Java installed. It will download Closure Compiler jar from the internet on the first run.
# All in all, if the page does not load for you correctly, start with disabling minification.
#
# Code below applies various optimizations to reduce size of the resulting html (with javascript).
# Folium output is repetitive and not optimized for situation where you have many polylines sharing their config.
#
# Effect on my sample of ˜2000 activities:
#   - original output from Folium:          8.77 MB
#   - after removing redundant definitions: 7.80 MB
#   - after compiling with Google Closure:  6.34 MB (i.e. overall reduction by ~28%)
#
# Note that your web server and browser likely support compression and therefore transferred size will be even less: 1.54 MB in my case.
def minify(filename: str) -> str:
    with open(filename, "r") as map_file:
        html = map_file.read()

    html_match = re.match(r"^(.+</body>\s*<script>)(.*)(</script>.*)$", html, re.DOTALL)
    js = html_match[2]

    # Each popup is initialized with maxWidth. There does not seem to be any effect and it can be removed.
    # Note that you can see this property explicitly in Python code when creating the popup. However, if you remove it from there, the
    # popups do not work.
    js = js.replace("{\"maxWidth\": 500}", "")
    # Popups have unique IDs and explicit style. None of this is needed.
    js = re.sub(" id=\"html_\\w+\" style=\"width: 100.0%; height: 100.0%;\"", "", js)

    # Definition of Polylines is too verbose. Each instance has its parameters explicitly defined even though all instances in one group
    # have the same set of parameters. Therefore, introducing a new function per group to create a Polyline to avoid duplication.
    #
    # L.polyline([[50.02206, 14.52665], [50.02196, 14.52708], [50.02143, 14.5274], [50.01971, 14.53054]],
    #            {"bubblingMouseEvents": true, "color": "magenta", "dashArray": null, "dashOffset": null, "fill": false, "fillColor": "magenta", "fillOpacity": 0.2, "fillRule": "evenodd", "lineCap": "round", "lineJoin": "round", "noClip": false, "opacity": 0.8, "smoothFactor": 3, "stroke": true, "weight": 3}
    #             ).addTo(feature_group_f39c438cc69f387c393faa4bab0135ef);
    #
    # becomes single definition of a function:
    # function polyLine5(coords) {
    #   return L.polyline(coords, {"bubblingMouseEvents": true, "color": "magenta", "dashArray": null, "dashOffset": null, "fill": false, "fillColor": "magenta", "fillOpacity": 0.2, "fillRule": "evenodd", "lineCap": "round", "lineJoin": "round", "noClip": false, "opacity": 0.8, "smoothFactor": 3, "stroke": true, "weight": 3})
    #       .addTo(feature_group_8f5528b1ae80f23917ad9b1df567802e)}
    #
    # and each polyline then has simplified definition:
    # polyline5([[50.02206, 14.52665], [50.02196, 14.52708], [50.02143, 14.5274], [50.01971, 14.53054]])
    class Group:
        def __init__(self, id, name, style):
            self.id = id
            self.name = name
            self.style = style
            self.method_name = f"polyLine{id}"
            self.method_def = f"function {self.method_name}(coords) {{ return L.polyline(coords, {style}).addTo({self.name})}}"

    groups = []
    pattern = re.compile(r"(L\.polyline\(\s+(\[\[.+\]\]),\s+({.+})\s+\)\.addTo\((\w+)\);)")
    for match in re.findall(pattern, js):
        whole = match[0]
        coords = match[1]
        style = match[2]
        group_name = match[3]

        group = None
        for g in groups:
            if g.name == group_name:
                group = g
        if not group:
            index = len(groups)
            group = Group(index, group_name, style)
            groups.append(group)
        js = js.replace(whole, f"{group.method_name}({coords});")

    for group in groups:
        js = group.method_def + js + "\n"

    # Write javascript to a separate file, run it through Google Closure Compiler and read it back to a variable
    with open("data/map.js", "w") as js_file:
        js_file.write(js)

    # See https://github.com/google/closure-compiler to learn more about the compiler
    if not os.path.exists("closure-compiler-v20240317.jar"):
        logger.info("Closure compiler jar file not found. Going to download it from Maven central")
        subprocess.run(
            "curl -LO https://repo1.maven.org/maven2/com/google/javascript/closure-compiler/v20240317/closure-compiler-v20240317.jar",
            shell=True)

    min_js_filename = "data/map.min.js"
    if os.path.exists(min_js_filename):
        os.remove(min_js_filename)
    logger.debug("Running closure compiler on the data/map.js")
    subprocess.run(
        "java -jar closure-compiler-v20240317.jar externs.js data/map.js --compilation_level ADVANCED --js_output_file data/map.min.js",
        shell=True)

    with open(min_js_filename, "r") as js_file:
        js = js_file.read()

    output_filename = filename.replace(".html", ".min.html")
    with open(output_filename, "w") as min_map_file:
        min_map_file.write(html_match[1])
        min_map_file.write(js)
        min_map_file.write(html_match[3])

    return output_filename
