function mapActivitiesToDate(leafletMap) {
    const resultMap = new Map();
    leafletMap.eachLayer(function(layer) {
        if (layer instanceof L.GeoJSON) {
            const popup = layer.getPopup();
            if (popup) {
                const contentElement = popup.getContent();
                const content = contentElement instanceof HTMLElement ? contentElement.innerHTML : contentElement;
                const dateMatch = content.match(/(\d{4}-\d{2}-\d{2})/);
                if (dateMatch) {
                    const date = new Date(dateMatch[0]);
                    resultMap.set(layer, date);
                }
            }
        }
    });
    return resultMap;
}

function getMinMaxDates(activitiesToDate) {
    const dates = Array.from(activitiesToDate.values());
    if (dates.length > 0) {
        const minDate = new Date(Math.min(...dates)).toISOString().split('T')[0];
        const maxDate = new Date(Math.max(...dates)).toISOString().split('T')[0];
        return [minDate, maxDate];
    } else {
        console.log('No dates found.');
        return null;
    }
}

// filter activities based on the selected date range
function filterActivities(leafletMap, activitiesToDate, startDate, endDate) {
    activitiesToDate.forEach((date, layer) => {
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

function findLeafletMapInstance() {
    const mapInstances = [];
    for (const prop in window) {
        if (window.hasOwnProperty(prop) && window[prop] instanceof L.Map) {
            return window[prop];
        }
    }
    alert("No Leaflet map found. Date filtering will not work.");
}

// initialize date-range slider
document.addEventListener('DOMContentLoaded', function () {
    const leafletMap = findLeafletMapInstance();
    const activitiesToDate = mapActivitiesToDate(leafletMap);
    [minDate, maxDate] = getMinMaxDates(activitiesToDate);

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
        filterActivities(leafletMap, activitiesToDate, startDate, endDate);
    });

});