function mapLayersToActivitiesToDate(mapControl) {
    const resultMap = new Map();

    Object.keys(mapControl.overlays).forEach(key => {
        const layerMap = new Map();

        mapControl.overlays[key].eachLayer(function(layer) {
            if (layer instanceof L.GeoJSON) {
                const popup = layer.getPopup();
                if (popup) {
                    const contentElement = popup.getContent();
                    const content = contentElement instanceof HTMLElement ? contentElement.innerHTML : contentElement;
                    const dateMatch = content.match(/(\d{4}-\d{2}-\d{2})/);
                    if (dateMatch) {
                        const date = new Date(dateMatch[0]);
                        layerMap.set(layer, date);
                    }
                }
            }
        });
        resultMap.set(key, layerMap);
    });

    return resultMap;
}

function getMinMaxDates(activitiesMap) {
    let min = Number.MAX_VALUE;
    let max = 0;
    activitiesMap.forEach((activitiesToDate) => {
        dates = Array.from(activitiesToDate.values());
        if (dates.length > 0) {
            min = Math.min(...dates, min);
            max = Math.max(...dates, max);
        }
    });

    if (min == Number.MAX_VALUE || max == 0) {
        console.log('No dates found.');
        return null;
    }

    const minDate = new Date(min).toISOString().split('T')[0];
    const maxDate = new Date(max).toISOString().split('T')[0];
    return [minDate, maxDate];
}

// filter activities based on the selected date range
function filterActivities(leafletMap, mapControl, activitiesMap, startDate, endDate) {
    activitiesMap.forEach((activitiesToDate, layerName) => {
        if (mapControl.overlays[layerName]._map) {
            activitiesToDate.forEach((date, layer) => {
                // TODO does not work well with activity type layer selection
                // When enabling a type layer, date range is not applied to its activities and all of them get displayed
                if (date >= startDate && date <= endDate) {
                    if (!leafletMap.hasLayer(layer)) {
                        leafletMap.addLayer(layer);
                    }
                } else {
                    if (leafletMap.hasLayer(layer)) {
                        leafletMap.removeLayer(layer);
                    }
                }
            });
        }
    });
}

function findLeafletMapAndControl() {
    let map, control;
    for (const prop in window) {
        if (window.hasOwnProperty(prop) && window[prop] instanceof L.Map) {
            map = window[prop];
        }
        else if (window.hasOwnProperty(prop) && window[prop] instanceof Object && window[prop].base_layers && window[prop].overlays) {
            control = window[prop];
        }
    }
    if (!map || !control) {
        alert("No Leaflet map or control layer found. Date filtering will not work.");
    }
    return [map, control];
}

// initialize date-range slider
document.addEventListener('DOMContentLoaded', function () {
    [leafletMap, mapControl] = findLeafletMapAndControl();
    const activitiesMap = mapLayersToActivitiesToDate(mapControl);
    [minDate, maxDate] = getMinMaxDates(activitiesMap);

    const dateSlider = document.getElementById('date-slider');
    const dateRange = document.getElementById('date-range');

    noUiSlider.create(dateSlider, {
        start: [new Date(minDate).getTime(), new Date(maxDate).getTime()],
        connect: true,
        range: {
            'min': new Date(minDate).getTime(),
            'max': new Date(maxDate).getTime()
        },
        tooltips: false,
        format: {
            to: function (value) {
                return new Date(value).toISOString().split('T')[0];
            },
            from: function (value) {
                return value;
            }
        }
    });

    dateSlider.noUiSlider.on('update', function (values, handle) {
        const startDate = new Date(values[0]);
        const endDate = new Date(values[1]);
        dateRange.innerHTML = values.join(' - ');
    });
    dateSlider.noUiSlider.on('set', function (values, handle) {
        const startDate = new Date(values[0]);
        const endDate = new Date(values[1]);
        filterActivities(leafletMap, mapControl, activitiesMap, startDate, endDate);
    });

});