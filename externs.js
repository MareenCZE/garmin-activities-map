/**
 * JavaScript definitions of "externs" for Google Closure Compiler which is used to reduce size of the output.
 *
 * @externs
 */

/*
 * Additions required for activities map on top of the Leaflet definitions below
 */
L.control.fullscreen = function(x) {};
L.control.locate = function(x) {};
const $ = function(x) {};

/*
 * Extern file for Leaflet, an open-source Javascript library for mobile-friendly
 * interactive maps.
 *
 * Copied from https://gist.github.com/PeterTillema/74117f5c7a2f2ff603b5ec5c95f83230 with minor adjustments (L.geoJSON -> L.geoJson)
 */

/**
 * @constructor
 */
function L() {}

/**
 * @typedef {L.LatLng|Array<number>|{lat:number, lng:number}}
 */
let ExpandedLatLng;
/**
 * @typedef {L.LatLngBounds|Array<Array<number>>}
 */
let ExpandedLatLngBounds;
/**
 * @typedef {L.Point|Array<number>|{x:number, y:number}}
 */
let ExpandedPoint;

/*******************************************************************************
 *                                     MAP                                     *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.Evented}
 */
L.Map = function() {}

/**
 * @param {string|HTMLElement} id
 * @param {(L.MapOptions|Object<string, *>)=} options
 * @constructs L.Map
 */
L.map = function(id, options) {}

/**
 * @record
 */
L.MapOptions = function() {}
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.preferCanvas;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.attributionControl;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.zoomControl;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.closePopupOnClick;
/** @type {?number|undefined} */
L.MapOptions.prototype.zoomSnap;
/** @type {?number|undefined} */
L.MapOptions.prototype.zoomDelta;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.trackResize;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.boxZoom;
/** @type {?Boolean|?string|undefined} */
L.MapOptions.prototype.doubleClickZoom;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.dragging;
/** @type {?L.CRS|undefined} */
L.MapOptions.prototype.crs;
/** @type {?L.LatLng|undefined} */
L.MapOptions.prototype.center;
/** @type {?number|undefined} */
L.MapOptions.prototype.zoom;
/** @type {?number|undefined} */
L.MapOptions.prototype.minZoom;
/** @type {?number|undefined} */
L.MapOptions.prototype.maxZoom;
/** @type {?Array<L.Layer>|undefined} */
L.MapOptions.prototype.layers;
/** @type {?L.LatLngBounds|undefined} */
L.MapOptions.prototype.maxBounds;
/** @type {?L.Renderer|undefined} */
L.MapOptions.prototype.renderer;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.zoomAnimation;
/** @type {?number|undefined} */
L.MapOptions.prototype.zoomAnimationThreshold;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.fadeAnimation;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.markerZoomAnimation;
/** @type {?number|undefined} */
L.MapOptions.prototype.transform3DLimit;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.inertia;
/** @type {?number|undefined} */
L.MapOptions.prototype.inertiaDeceleration;
/** @type {?number|undefined} */
L.MapOptions.prototype.inertiaMaxSpeed;
/** @type {?number|undefined} */
L.MapOptions.prototype.easeLinearity;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.worldCopyJump;
/** @type {?number|undefined} */
L.MapOptions.prototype.maxBoundsViscosity;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.keyboard;
/** @type {?number|undefined} */
L.MapOptions.prototype.keyboardPanDelta;
/** @type {?Boolean|?string|undefined} */
L.MapOptions.prototype.scrollWheelZoom;
/** @type {?number|undefined} */
L.MapOptions.prototype.wheelDebounceTime;
/** @type {?number|undefined} */
L.MapOptions.prototype.wheelPxPerZoomLevel;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.tap;
/** @type {?number|undefined} */
L.MapOptions.prototype.tapTolerance;
/** @type {?Boolean|?string|undefined} */
L.MapOptions.prototype.touchZoom;
/** @type {?Boolean|undefined} */
L.MapOptions.prototype.bounceAtZoomLimits;

/*******************************************************************************
 *                                  MAP METHODS                                *
 *******************************************************************************/

/**
 * @param {L.Path} layer
 * @returns {L.Renderer}
 */
L.Map.prototype.getRenderer = function(layer) {}
/**
 * @param {L.Control} control
 * @returns {L.Map}
 */
L.Map.prototype.addControl = function(control) {}
/**
 * @param {L.Control} control
 * @returns {L.Map}
 */
L.Map.prototype.removeControl = function(control) {}
/**
 * @param {L.Layer} control
 * @returns {L.Map}
 */
L.Map.prototype.addLayer = function(control) {}
/**
 * @param {L.Layer} control
 * @returns {L.Map}
 */
L.Map.prototype.removeLayer = function(control) {}
/**
 * @param {L.Layer} control
 * @returns {Boolean}
 */
L.Map.prototype.hasLayer = function(control) {}
/**
 * @param {function(L.Layer)} fn
 * @param {Object=} context
 * @returns {L.Map}
 */
L.Map.prototype.eachLayer = function(fn, context) {}
/**
 * @param {L.Popup|string|HTMLElement} popup
 * @param {ExpandedLatLng=} latlng
 * @param {(L.PopupOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.openPopup = function(popup, latlng, options) {}
/**
 * @param {L.Popup} popup
 * @returns {L.Map}
 */
L.Map.prototype.closePopup = function(popup) {}
/**
 * @param {L.Tooltip|string|HTMLElement} Tooltip
 * @param {ExpandedLatLng=} latlng
 * @param {(L.TooltipOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.openTooltip = function(Tooltip, latlng, options) {}
/**
 * @param {L.Tooltip} Tooltip
 * @returns {L.Map}
 */
L.Map.prototype.closeTooltip = function(Tooltip) {}
/**
 * @param {ExpandedLatLng} center
 * @param {number} zoom
 * @param {(L.ZoomPanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.setView = function(center, zoom, options) {}
/**
 * @param {number} zoom
 * @param {(L.ZoomPanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.setZoom = function(zoom, options) {}
/**
 * @param {number=} delta
 * @param {(L.ZoomOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.zoomIn = function(delta, options) {}
/**
 * @param {number=} delta
 * @param {(L.ZoomOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.zoomOut = function(delta, options) {}
/**
 * @param {ExpandedLatLng|ExpandedPoint} latlng
 * @param {number} zoom
 * @param {(L.ZoomOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.setZoomAround = function(latlng, zoom, options) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.FitBoundsOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.fitBounds = function(bounds, options) {}
/**
 * @param {(L.FitBoundsOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.fitWorld = function(options) {}
/**
 * @param {ExpandedLatLng} latlng
 * @param {(L.PanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.panTo = function(latlng, options) {}
/**
 * @param {ExpandedPoint} offset
 * @param {(L.PanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.panBy = function(offset, options) {}
/**
 * @param {ExpandedLatLng} latlng
 * @param {number=} zoom
 * @param {(L.ZoomPanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.flyTo = function(latlng, zoom, options) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.FitBoundsOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.flyToBounds = function(bounds, options) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @returns {L.Map}
 */
L.Map.prototype.setMaxBounds = function(bounds) {}
/**
 * @param {number} zoom
 * @returns {L.Map}
 */
L.Map.prototype.setMinZoom = function(zoom) {}
/**
 * @param {number} zoom
 * @returns {L.Map}
 */
L.Map.prototype.setMaxZoom = function(zoom) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.PanOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.panInsideBounds = function(bounds, options) {}
/**
 * @param {ExpandedLatLng} latlng
 * @param {Object=} options
 * @returns {L.Map}
 */
L.Map.prototype.panInside = function(latlng, options) {}
/**
 * @param {L.ZoomPanOptions|Object<string, *>|Boolean} options
 * @returns {L.Map}
 */
L.Map.prototype.invalidateSize = function(options) {}
/**
 * @returns {L.Map}
 */
L.Map.prototype.stop = function() {}
/**
 * @param {(L.LocateOptions|Object<string, *>)=} options
 * @returns {L.Map}
 */
L.Map.prototype.locate = function(options) {}
/**
 * @returns {L.Map}
 */
L.Map.prototype.stopLocate = function() {}
/**
 * @param {string} name
 * @param {function(*)} handlerClass
 * @returns {L.Map}
 */
L.Map.prototype.addHandler = function(name, handlerClass) {}
/**
 * @returns {L.Map}
 */
L.Map.prototype.remove = function() {}
/**
 * @param {string} name
 * @param {HTMLElement=} container
 * @returns {HTMLElement}
 */
L.Map.prototype.createPane = function(name, container) {}
/**
 * @param {string|HTMLElement} pane
 * @returns {HTMLElement}
 */
L.Map.prototype.getPane = function(pane) {}
/**
 * @returns {Object}
 */
L.Map.prototype.getPanes = function() {}
/**
 * @returns {HTMLElement}
 */
L.Map.prototype.getContainer = function() {}
/**
 * @param {function(*)} fn
 * @param {Object=} context
 */
L.Map.prototype.whenReady = function(fn, context) {}
/**
 * @returns {L.LatLng}
 */
L.Map.prototype.getCenter = function() {}
/**
 * @returns {number}
 */
L.Map.prototype.getZoom = function() {}
/**
 * @returns {L.LatLngBounds}
 */
L.Map.prototype.getBounds = function() {}
/**
 * @returns {number}
 */
L.Map.prototype.getMinZoom = function() {}
/**
 * @returns {number}
 */
L.Map.prototype.getMaxZoom = function() {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @param {Boolean=} inside
 * @param {ExpandedPoint=} padding
 */
L.Map.prototype.getBoundsZoom = function(bounds, inside, padding) {}
/**
 * @returns {L.Point}
 */
L.Map.prototype.getSize = function() {}
/**
 * @returns {L.Bounds}
 */
L.Map.prototype.getPixelBounds = function() {}
/**
 * @returns {L.Point}
 */
L.Map.prototype.getPixelOrigin = function() {}
/**
 * @param {number=} zoom
 * @returns {L.Bounds}
 */
L.Map.prototype.getPixelWorldBounds = function(zoom) {}
/**
 * @param {number} toZoom
 * @param {number} fromZoom
 * @returns {number}
 */
L.Map.prototype.getZoomScale = function(toZoom, fromZoom) {}
/**
 * @param {number} scale
 * @param {number} fromZoom
 * @returns {number}
 */
L.Map.prototype.getScaleZoom = function(scale, fromZoom) {}
/**
 * @param {L.Layer} latlng
 * @param {number} zoom
 * @returns {L.Point}
 */
L.Map.prototype.project = function(latlng, zoom) {}
/**
 * @param {ExpandedPoint} point
 * @param {number} zoom
 * @returns {L.LatLng}
 */
L.Map.prototype.unproject = function(point, zoom) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.LatLng}
 */
L.Map.prototype.layerPointToLatLng = function(point) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Point}
 */
L.Map.prototype.latLngToLayerPoint = function(latlng) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.LatLng}
 */
L.Map.prototype.wrapLatLng = function(latlng) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @returns {L.LatLngBounds}
 */
L.Map.prototype.wrapLatLngBounds = function(bounds) {}
/**
 * @param {ExpandedLatLng} latlng1
 * @param {ExpandedLatLng} latlng2
 * @returns {number}
 */
L.Map.prototype.distance = function(latlng1, latlng2) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.Point}
 */
L.Map.prototype.containerPointToLayerPoint = function(point) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.Point}
 */
L.Map.prototype.layerPointToContainerPoint = function(point) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.LatLng}
 */
L.Map.prototype.containerPointToLatLng = function(point) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Point}
 */
L.Map.prototype.latLngToContainerPoint = function(latlng) {}
/**
 * @param {L.MouseEvent} ev
 * @returns {L.Point}
 */
L.Map.prototype.mouseEventToContainerPoint = function(ev) {}
/**
 * @param {L.MouseEvent} ev
 * @returns {L.Point}
 */
L.Map.prototype.mouseEventToLayerPoint = function(ev) {}
/**
 * @param {L.MouseEvent} ev
 * @returns {L.LatLng}
 */
L.Map.prototype.mouseEventToLatLng = function(ev) {}

/*******************************************************************************
 *                                    MAP MISC                                 *
 *******************************************************************************/

/** @type {L.ControlZoom} */
L.Map.zoomControl;
/** @type {L.Handler} */
L.Map.boxZoom;
/** @type {L.Handler} */
L.Map.doubleClickZoom;
/** @type {L.Handler} */
L.Map.dragging;
/** @type {L.Handler} */
L.Map.keyboard;
/** @type {L.Handler} */
L.Map.scrollWheelZoom;
/** @type {L.Handler} */
L.Map.tap;
/** @type {L.Handler} */
L.Map.touchZoom;

/**
 * @record
 */
L.LocateOptions = function() {}
/** @type {?Boolean|undefined} */
L.LocateOptions.prototype.watch;
/** @type {?Boolean|undefined} */
L.LocateOptions.prototype.setView;
/** @type {?number|undefined} */
L.LocateOptions.prototype.maxZoom;
/** @type {?number|undefined} */
L.LocateOptions.prototype.timeout;
/** @type {?number|undefined} */
L.LocateOptions.prototype.maximumAge;
/** @type {?Boolean|undefined} */
L.LocateOptions.prototype.enableHighAccuracy;

/**
 * @record
 */
L.ZoomOptions = function() {}
/** @type {?Boolean|undefined} */
L.ZoomOptions.prototype.animate;

/**
 * @record
 */
L.PanOptions = function() {}
/** @type {?Boolean|undefined} */
L.PanOptions.prototype.animate;
/** @type {?number|undefined} */
L.PanOptions.prototype.duration;
/** @type {?number|undefined} */
L.PanOptions.prototype.easeLinearity;
/** @type {?Boolean|undefined} */
L.PanOptions.prototype.noMoveStart;

/**
 * @record
 * @extends {L.ZoomOptions}
 * @extends {L.PanOptions}
 */
L.ZoomPanOptions = function() {}

/**
 * @record
 * @extends {L.ZoomOptions}
 * @extends {L.PanOptions}
 */
L.FitBoundsOptions = function() {}
/** @type {?L.Point|undefined} */
L.FitBoundsOptions.prototype.paddingTopLeft;
/** @type {?L.Point|undefined} */
L.FitBoundsOptions.prototype.paddingBottomRight;
/** @type {?L.Point|undefined} */
L.FitBoundsOptions.prototype.padding;
/** @type {?number|undefined} */
L.FitBoundsOptions.prototype.maxZoom;

/*******************************************************************************
 *                                  UI LAYERS                                  *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.Layer}
 */
L.Marker = function() {}

/**
 * @param {ExpandedLatLng} latlng
 * @param {(L.MarkerOptions|Object<string, *>)=} options
 * @constructs L.Marker
 */
L.marker = function(latlng, options) {}

/**
 * @constructor
 * @extends {L.InteractiveLayerOptions}
 */
L.MarkerOptions = function() {}
/** @type {?L.Icon|undefined} */
L.MarkerOptions.prototype.icon;
/** @type {?Boolean|undefined} */
L.MarkerOptions.prototype.keyboard;
/** @type {?string|undefined} */
L.MarkerOptions.prototype.title;
/** @type {?string|undefined} */
L.MarkerOptions.prototype.alt;
/** @type {?number|undefined} */
L.MarkerOptions.prototype.zIndexOffset;
/** @type {?number|undefined} */
L.MarkerOptions.prototype.opacity;
/** @type {?Boolean|undefined} */
L.MarkerOptions.prototype.riseOnHover;
/** @type {?number|undefined} */
L.MarkerOptions.prototype.riseOffset;
/** @type {?string|undefined} */
L.MarkerOptions.prototype.pane;
/** @type {?string|undefined} */
L.MarkerOptions.prototype.shadowPane;
/** @type {?Boolean|undefined} */
L.MarkerOptions.prototype.bubblingMouseEvents;
/** @type {?Boolean|undefined} */
L.MarkerOptions.prototype.draggable;
/** @type {?Boolean|undefined} */
L.MarkerOptions.prototype.autoPan;
/** @type {?L.Point|undefined} */
L.MarkerOptions.prototype.autoPanPadding;
/** @type {?number|undefined} */
L.MarkerOptions.prototype.autoPanSpeed;

/**
 * @returns {L.LatLng}
 */
L.Marker.prototype.getLatLng = function() {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Marker}
 */
L.Marker.prototype.setLatLng = function(latlng) {}
/**
 * @param {number} offset
 * @returns {L.Marker}
 */
L.Marker.prototype.setZIndexOffset = function(offset) {}
/**
 * @returns {L.Icon}
 */
L.Marker.prototype.getIcon = function() {}
/**
 * @param {L.Icon} icon
 * @returns {L.Marker}
 */
L.Marker.prototype.setIcon = function(icon) {}
/**
 * @param {number} opacity
 * @returns {L.Marker}
 */
L.Marker.prototype.setOpacity = function(opacity) {}
/**
 * @param {number=} precision
 * @returns {Object}
 */
L.Marker.prototype.toGeoJSON = function(precision) {}

/** @type {L.Handler} */
L.Marker.dragging;

/**
 * @constructor
 * @extends {L.DivOverlay}
 */
L.Popup = function() {}

/**
 * @param {(L.PopupOptions|Object<string, *>)=} options
 * @param {L.Layer=} source
 * @constructs L.Popup
 */
L.popup = function(options, source) {}

/**
 * @constructor
 * @extends {L.DivOverlayOptions}
 */
L.PopupOptions = function() {}
/** @type {?number|undefined} */
L.PopupOptions.prototype.maxWidth;
/** @type {?number|undefined} */
L.PopupOptions.prototype.minWidth;
/** @type {?number|undefined} */
L.PopupOptions.prototype.maxHeight;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.autoPan;
/** @type {?L.Point|undefined} */
L.PopupOptions.prototype.autoPanPaddingTopLeft;
/** @type {?L.Point|undefined} */
L.PopupOptions.prototype.autoPanPaddingBottomRight;
/** @type {?L.Point|undefined} */
L.PopupOptions.prototype.autoPanPadding;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.keepInView;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.closeButton;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.autoClose;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.closeOnEscapeKey;
/** @type {?Boolean|undefined} */
L.PopupOptions.prototype.closeOnClick;
/** @type {?string|undefined} */
L.PopupOptions.prototype.className;

/**
 * @returns {L.LatLng}
 */
L.Popup.prototype.getLatLng = function() {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Popup}
 */
L.Popup.prototype.setLatLng = function(latlng) {}
/**
 * @returns {L.LatLng}
 */
L.Popup.prototype.getContent = function() {}
/**
 * @param {string|HTMLElement|function(L.Layer):string|HTMLElement} htmlContent
 * @returns {L.Popup}
 */
L.Popup.prototype.setContent = function(htmlContent) {}
/**
 * @returns {string|HTMLElement}
 */
L.Popup.prototype.getElement = function() {}
L.Popup.prototype.update = function() {}
/**
 * @returns {Boolean}
 */
L.Popup.prototype.isOpen = function() {}
/**
 * @returns {L.Popup}
 */
L.Popup.prototype.bringToFront = function() {}
/**
 * @returns {L.Popup}
 */
L.Popup.prototype.bringToBack = function() {}
/**
 * @param {L.Map} map
 * @returns {L.Popup}
 */
L.Popup.prototype.openOn = function(map) {}

/**
 * @constructor
 * @extends {L.DivOverlay}
 */
L.Tooltip = function() {}

/**
 * @param {L.TooltipOptions=} options
 * @param {L.Layer=} source
 * @constructs L.Tooltip
 */
L.tooltip = function(options, source) {}

/**
 * @constructor
 * @extends {L.DivOverlayOptions}
 */
L.TooltipOptions = function() {}
/** @type {?string|undefined} */
L.TooltipOptions.prototype.pane;
/** @type {?L.Point|undefined} */
L.TooltipOptions.prototype.offset;
/** @type {?string|undefined} */
L.TooltipOptions.prototype.direction;
/** @type {?Boolean|undefined} */
L.TooltipOptions.prototype.permanent;
/** @type {?Boolean|undefined} */
L.TooltipOptions.prototype.sticky;
/** @type {?Boolean|undefined} */
L.TooltipOptions.prototype.interactive;
/** @type {?number|undefined} */
L.TooltipOptions.prototype.opacity;

/*******************************************************************************
 *                                RASTER LAYERS                                *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.GridLayer}
 */
L.TileLayer = function() {}

/**
 * @param {string} urlTemplate
 * @param {(L.TileLayerOptions|Object<string, *>)=} options
 * @constructs L.TileLayer
 */
L.tileLayer = function(urlTemplate, options) {}

/**
 * @constructor
 * @extends {L.GridLayerOptions}
 */
L.TileLayerOptions = function() {}
/** @type {?number|undefined} */
L.TileLayerOptions.prototype.minZoom;
/** @type {?number|undefined} */
L.TileLayerOptions.prototype.maxZoom;
/** @type {?string|?Array<string>|undefined} */
L.TileLayerOptions.prototype.subdomains;
/** @type {?string|undefined} */
L.TileLayerOptions.prototype.errorTileUrl;
/** @type {?number|undefined} */
L.TileLayerOptions.prototype.zoomOffset;
/** @type {?Boolean|undefined} */
L.TileLayerOptions.prototype.tms;
/** @type {?Boolean|undefined} */
L.TileLayerOptions.prototype.zoomReverse;
/** @type {?Boolean|undefined} */
L.TileLayerOptions.prototype.detectRetina;
/** @type {?Boolean|?string|undefined} */
L.TileLayerOptions.prototype.crossOrigin;

/**
 * @param {string} url
 * @param {Boolean=} noRedraw
 * @returns {L.TileLayer}
 */
L.TileLayer.prototype.setUrl = function(url, noRedraw) {}
/**
 * @param {Object} coords
 * @param {function(*)=} done
 * @returns {HTMLElement}
 */
L.TileLayer.prototype.createTile = function(coords, done) {}
/**
 * @param {Object} coords
 * @returns {string}
 */
L.TileLayer.prototype.getTileUrl = function(coords) {}

/**
 * @constructor
 * @extends {L.TileLayer}
 */
L.TileLayerWMS = function() {}

/**
 * @param {string} baseUrl
 * @param {(L.TileLayerWMSOptions|Object<string, *>)=} options
 * @constructs L.TileLayerWMS
 */
L.tileLayer.wms = function(baseUrl, options) {}

/**
 * @constructor
 * @extends {L.TileLayerOptions}
 */
L.TileLayerWMSOptions = function() {}
/** @type {?string|undefined} */
L.TileLayerWMSOptions.prototype.layers;
/** @type {?string|undefined} */
L.TileLayerWMSOptions.prototype.styles;
/** @type {?string|undefined} */
L.TileLayerWMSOptions.prototype.format;
/** @type {?Boolean|undefined} */
L.TileLayerWMSOptions.prototype.transparent;
/** @type {?string|undefined} */
L.TileLayerWMSOptions.prototype.version;
/** @type {?L.CRS|undefined} */
L.TileLayerWMSOptions.prototype.crs;
/** @type {?Boolean|undefined} */
L.TileLayerWMSOptions.prototype.uppercase;

/**
 * @param {Object} params
 * @param {Boolean=} noRedraw
 * @returns {L.TileLayerWMS}
 */
L.TileLayerWMS.prototype.setParams = function(params, noRedraw) {}

/**
 * @constructor
 * @extends {L.Layer}
 */
L.ImageOverlay = function() {}

/**
 * @param {string} imageUrl
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.ImageOverlayOptions|Object<string, *>)=} options
 * @constructs L.ImageOverlay
 */
L.imageOverlay = function(imageUrl, bounds, options) {}

/**
 * @constructor
 * @extends {L.InteractiveLayerOptions}
 */
L.ImageOverlayOptions = function() {}
/** @type {?number|undefined} */
L.ImageOverlayOptions.prototype.opacity;
/** @type {?string|undefined} */
L.ImageOverlayOptions.prototype.alt;
/** @type {?Boolean|undefined} */
L.ImageOverlayOptions.prototype.interactive;
/** @type {?Boolean|?string|undefined} */
L.ImageOverlayOptions.prototype.crossOrigin;
/** @type {?string|undefined} */
L.ImageOverlayOptions.prototype.errorOverlayUrl;
/** @type {?number|undefined} */
L.ImageOverlayOptions.prototype.zIndex;
/** @type {?string|undefined} */
L.ImageOverlayOptions.prototype.className;

/**
 * @param {number} opacity
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.setOpacity = function(opacity) {}
/**
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.bringToFront = function() {}
/**
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.bringToBack = function() {}
/**
 * @param {string} url
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.setUrl = function(url) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.setBounds = function(bounds) {}
/**
 * @param {number} value
 * @returns {L.ImageOverlay}
 */
L.ImageOverlay.prototype.setZIndex = function(value) {}
/**
 * @returns {L.LatLngBounds}
 */
L.ImageOverlay.prototype.getBounds = function() {}
/**
 * @returns {HTMLElement}
 */
L.ImageOverlay.prototype.getElement = function() {}

/**
 * @constructor
 * @extends {L.ImageOverlay}
 */
L.VideoOverlay = function() {}

/**
 * @param {string|Array|HTMLVideoElement} video
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.VideoOverlayOptions|Object<string, *>)=} options
 * @constructs L.VideoOverlay
 */
L.videoOverlay = function(video, bounds, options) {}

/**
 * @constructor
 * @extends {L.ImageOverlayOptions}
 */
L.VideoOverlayOptions = function() {}
/** @type {?Boolean|undefined} */
L.VideoOverlayOptions.prototype.autoplay;
/** @type {?Boolean|undefined} */
L.VideoOverlayOptions.prototype.loop;
/** @type {?Boolean|undefined} */
L.VideoOverlayOptions.prototype.keepAspectRatio;
/** @type {?Boolean|undefined} */
L.VideoOverlayOptions.prototype.muted;

/**
 * @returns {HTMLVideoElement}
 */
L.VideoOverlay.prototype.getElement = function() {}

/**
 * @constructor
 * @extends {L.ImageOverlay}
 */
L.SVGElement = function() {}

/**
 * @param {string|SVGElement} svg
 * @param {ExpandedLatLngBounds} bounds
 * @param {(L.SVGOverlayOptions|Object<string, *>)=} options
 * @constructs L.SVGElement
 */
L.svgOverlay = function(svg, bounds, options) {}

/**
 * @constructor
 * @extends {L.ImageOverlayOptions}
 */
L.SVGOverlayOptions = function() {}

/**
 * @returns {SVGElement}
 */
L.svgOverlay.prototype.getElement = function() {}

/*******************************************************************************
 *                                VECTOR LAYERS                                *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.Layer}
 */
L.Path = function() {}

/**
 * @constructor
 * @extends {L.InteractiveLayerOptions}
 */
L.PathOptions = function() {}
/** @type {?Boolean|undefined} */
L.PathOptions.prototype.stroke;
/** @type {?string|undefined} */
L.PathOptions.prototype.color;
/** @type {?number|undefined} */
L.PathOptions.prototype.weight;
/** @type {?number|undefined} */
L.PathOptions.prototype.opacity;
/** @type {?string|undefined} */
L.PathOptions.prototype.lineCap;
/** @type {?string|undefined} */
L.PathOptions.prototype.lineJoin;
/** @type {?string|undefined} */
L.PathOptions.prototype.dashArray;
/** @type {?string|undefined} */
L.PathOptions.prototype.dashOffset;
/** @type {?Boolean|undefined} */
L.PathOptions.prototype.fill;
/** @type {?string|undefined} */
L.PathOptions.prototype.fillColor;
/** @type {?number|undefined} */
L.PathOptions.prototype.fillOpacity;
/** @type {?string|undefined} */
L.PathOptions.prototype.fillRule;
/** @type {?Boolean|undefined} */
L.PathOptions.prototype.bubblingMouseEvents;
/** @type {?L.Renderer|undefined} */
L.PathOptions.prototype.renderer;
/** @type {?string|undefined} */
L.PathOptions.prototype.className;
/**
 * @returns {L.Path}
 */
L.Path.prototype.redraw = function() {}
/**
 * @param {L.PathOptions} style
 * @returns {L.Path}
 */
L.Path.prototype.setStyle = function(style) {}
/**
 * @returns {L.Path}
 */
L.Path.prototype.bringToFront = function() {}
/**
 * @returns {L.Path}
 */
L.Path.prototype.bringToBack = function() {}

/**
 * @constructor
 * @extends {L.Path}
 */
L.Polyline = function() {}

/**
 * @param {Array<ExpandedLatLng>} latlngs
 * @param {(L.PolylineOptions|Object<string, *>)=} options
 * @constructs L.Polyline
 */
L.polyline = function(latlngs, options) {}

/**
 * @constructor
 * @extends {L.PathOptions}
 */
L.PolylineOptions = function() {}
/** @type {?number|undefined} */
L.PolylineOptions.prototype.smoothFactor;
/** @type {?Boolean|undefined} */
L.PolylineOptions.prototype.noClip;

/**
 * @param {number=} precision
 * @returns {Object}
 */
L.Polyline.prototype.toGeoJSON = function(precision) {}
/**
 * @returns {Array<L.LatLng>}
 */
L.Polyline.prototype.getLatLngs = function() {}
/**
 * @param {Array<ExpandedLatLng>} latlngs
 * @returns {L.Polyline}
 */
L.Polyline.prototype.setLatLngs = function(latlngs) {}
/**
 * @returns {Boolean}
 */
L.Polyline.prototype.isEmpty = function() {}
/**
 * @param {ExpandedPoint} p
 * @returns {L.Point}
 */
L.Polyline.prototype.closestLayerPoint = function(p) {}
/**
 * @returns {L.LatLng}
 */
L.Polyline.prototype.getCenter = function() {}
/**
 * @returns {L.LatLngBounds}
 */
L.Polyline.prototype.getBounds = function() {}
/**
 * @param {ExpandedLatLng} latlng
 * @param {Array<ExpandedLatLng>=} latlngs
 * @returns {L.Polyline}
 */
L.Polyline.prototype.addLatLng = function(latlng, latlngs) {}

/**
 * @constructor
 * @extends {L.Polyline}
 */
L.Polygon = function() {}

/**
 * @param {Array<ExpandedLatLng>} latlngs
 * @param {(L.PolylineOptions|Object<string, *>)=} options
 * @constructs L.Polygon
 */
L.polygon = function(latlngs, options) {}

/**
 * @param {number=} precision
 * @returns {Object}
 */
L.Polygon.prototype.toGeoJSON = function(precision) {}

/**
 * @constructor
 * @extends {L.Polygon}
 */
L.Rectangle = function() {}

/**
 * @param {ExpandedLatLngBounds} latLngBounds
 * @param {(L.PolylineOptions|Object<string, *>)=} options
 * @constructs L.Rectangle
 */
L.rectangle = function(latLngBounds, options) {}

/**
 * @param {ExpandedLatLngBounds} latLngBounds
 * @returns {L.Rectangle}
 */
L.Rectangle.prototype.setBounds = function(latLngBounds) {}

/**
 * @constructor
 * @extends {L.CircleMarker}
 */
L.Circle = function() {}

/**
 * @param {ExpandedLatLng} latlng
 * @param {(L.CircleOptions|Object<string, *>|number)=} radius
 * @param {(L.CircleOptions|Object<string, *>)=} options
 * @constructs L.Circle
 */
L.circle = function(latlng, radius, options) {}

/**
 * @constructor
 * @extends {L.CircleMarkerOptions}
 */
L.CircleOptions = function() {}
/** @type {?number|undefined} */
L.CircleOptions.prototype.radius;

/**
 * @param {number} radius
 * @returns {L.Circle}
 */
L.Circle.prototype.setRadius = function(radius) {}
/**
 * @returns {number}
 */
L.Circle.prototype.getRadius = function () {}
/**
 * @returns {L.LatLngBounds}
 */
L.Circle.prototype.getBounds = function() {}

/**
 * @constructor
 * @extends {L.Path}
 */
L.CircleMarker = function() {}

/**
 * @param {ExpandedLatLng} latlng
 * @param {(L.CircleMarkerOptions|Object<string, *>)=} options
 * @constructs L.CircleMarker
 */
L.circleMarker = function(latlng, options) {}

/**
 * @constructor
 * @extends {L.PathOptions}
 */
L.CircleMarkerOptions = function() {}
/** @type {?number|undefined} */
L.CircleMarkerOptions.prototype.radius;

/**
 * @param {number=} precision
 * @returns {Object}
 */
L.CircleMarker.prototype.toGeoJSON = function(precision) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.CircleMarker}
 */
L.CircleMarker.prototype.setLatLng = function(latlng) {}
/**
 * @returns {L.LatLng}
 */
L.CircleMarker.prototype.getLatLng = function() {}
/**
 * @param {number} radius
 * @returns {L.CircleMarker}
 */
L.CircleMarker.prototype.setRadius = function(radius) {}
/**
 * @returns {number}
 */
L.CircleMarker.prototype.getRadius = function() {}

/**
 * @constructor
 * @extends {L.Renderer}
 */
L.SVG = function() {}

/**
 * @param {(L.RendererOptions|Object<string, *>)=} options
 * @constructs L.SVG
 */
L.svg = function(options) {}

/**
 * @param {string} name
 * @returns {SVGElement}
 */
L.SVG.create = function(name) {}
/**
 * @param {Array<ExpandedPoint>} rings
 * @param {Boolean} closed
 * @returns {string}
 */
L.SVG.pointsToPath = function(rings, closed) {}

/**
 * @constructor
 * @extends {L.Renderer}
 */
L.Canvas = function() {}

/**
 * @param {(L.RendererOptions|Object<string, *>)=} options
 * @constructs L.Canvas
 */
L.canvas = function(options) {}

/*******************************************************************************
 *                                OTHER LAYERS                                 *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.Layer}
 */
L.LayerGroup = function() {}

/**
 * @param {Array<L.Layer>=} layers
 * @param {(L.LayerOptions|Object<string, *>)=} options
 * @constructs L.LayerGroup
 */
L.layerGroup = function(layers, options) {}

/**
 * @param {number=} precision
 * @returns {Object}
 */
L.LayerGroup.prototype.toGeoJSON = function(precision) {}
/**
 * @param {L.Layer} layer
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.addLayer = function(layer) {}
/**
 * @param {L.Layer|number} layer
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.removeLayer = function(layer) {}
/**
 * @param {L.Layer|number} layer
 * @returns {Boolean}
 */
L.LayerGroup.prototype.hasLayer = function(layer) {}
/**
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.clearLayers = function() {}
/**
 * @param {string} methodName
 * @param {...} args
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.invoke = function(methodName, args) {}
/**
 * @param {function(L.Layer)} fn
 * @param {Object=} context
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.eachLayer = function(fn, context) {}
/**
 * @param {number} id
 * @returns {L.Layer}
 */
L.LayerGroup.prototype.getLayer = function(id) {}
/**
 * @returns {Array<L.Layer>}
 */
L.LayerGroup.prototype.getLayers = function() {}
/**
 * @param {number} zIndex
 * @returns {L.LayerGroup}
 */
L.LayerGroup.prototype.setZIndex = function(zIndex) {}
/**
 * @param {L.Layer} layer
 * @returns {number}
 */
L.LayerGroup.prototype.getLayerId = function(layer) {}

/**
 * @constructor
 * @extends {L.LayerGroup}
 */
L.FeatureGroup = function() {}

/**
 * @param {Array<L.Layer>|Object} layers
 * @param {(L.LayerOptions|Object<string, *>)=} options
 * @constructs L.FeatureGroup
 */
L.featureGroup = function(layers, options) {}

/**
 * @param {L.PathOptions} style
 * @returns {L.FeatureGroup}
 */
L.FeatureGroup.prototype.setStyle = function(style) {}
/**
 * @returns {L.FeatureGroup}
 */
L.FeatureGroup.prototype.bringToFront = function() {}
/**
 * @returns {L.FeatureGroup}
 */
L.FeatureGroup.prototype.bringToBack = function() {}
/**
 * @returns {L.LatLngBounds}
 */
L.FeatureGroup.prototype.getBounds = function() {}

/**
 * @constructor
 * @extends {L.FeatureGroup}
 */
L.GeoJSON = function() {}

/**
 * @param {Object=} geojson
 * @param {(?L.GeoJSONOptions|Object<string, *>)=} options
 * @constructs {L.GeoJSON
 */
L.geoJson = function(geojson, options) {}

/**
 * @constructor
 * @extends {L.LayerOptions}
 */
L.GeoJSONOptions = function() {}
/** @type {?Function|undefined} */
L.GeoJSONOptions.prototype.pointToLayer;
/** @type {?Function|undefined} */
L.GeoJSONOptions.prototype.style;
/** @type {?Function|undefined} */
L.GeoJSONOptions.prototype.onEachFeature;
/** @type {?Function|undefined} */
L.GeoJSONOptions.prototype.filter;
/** @type {?Function|undefined} */
L.GeoJSONOptions.prototype.coordsToLatLng;
/** @type {?Boolean|undefined} */
L.GeoJSONOptions.prototype.markersInheritOptions;

/**
 * @param {Object} data
 * @returns {L.GeoJSON}
 */
L.GeoJSON.prototype.addData = function(data) {}
/**
 * @param {L.Path=} layer
 * @returns {L.GeoJSON}
 */
L.GeoJSON.prototype.resetStyle = function(layer) {}
/**
 * @param {Function} style
 * @returns {L.GeoJSON}
 */
L.GeoJSON.prototype.setStyle = function(style) {}

/**
 * @param {Object} featureData
 * @param {(?L.GeoJSONOptions|Object<string, *>)=} options
 * @returns {L.Layer}
 */
L.GeoJSON.geometryToLayer = function(featureData, options) {}
/**
 * @param {Array} coords
 * @returns {L.LatLng}
 */
L.GeoJSON.coordsToLatLng = function(coords) {}
/**
 * @param {Array} coords
 * @param {number=} levelsDeep
 * @param {Function=} coordsToLatLng
 * @returns {Array}
 */
L.GeoJSON.coordsToLatLngs = function(coords, levelsDeep, coordsToLatLng) {}
/**
 * @param {ExpandedLatLng} latlng
 * @param {number=} precision
 * @returns {Array}
 */
L.GeoJSON.latLngToCoords = function(latlng, precision) {}
/**
 * @param {Array} latlngs
 * @param {number=} levelsDeep
 * @param {Boolean=} closed
 * @returns {Array}
 */
L.GeoJSON.latLngsToCoords = function(latlngs, levelsDeep, closed) {}
/**
 * @param {Object} geojson
 * @returns {Object}
 */
L.GeoJSON.asFeature = function(geojson) {}

/**
 * @constructor
 * @extends {L.Layer}
 */
L.GridLayer = function() {}

/**
 * @param {(?L.GridLayerOptions|Object<string, *>)=} options
 * @constructs L.GridLayer
 */
L.gridLayer = function(options) {}

/**
 * @constructor
 * @extends {L.LayerOptions}
 */
L.GridLayerOptions = function() {}
/** @type {?number|?L.Point|undefined} */
L.GridLayerOptions.prototype.tileSize;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.opacity;
/** @type {?Boolean|undefined} */
L.GridLayerOptions.prototype.updateWhenIdle;
/** @type {?Boolean|undefined} */
L.GridLayerOptions.prototype.updateWhenZooming;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.updateInterval;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.zIndex;
/** @type {?L.LatLngBounds|undefined} */
L.GridLayerOptions.prototype.bounds;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.minZoom;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.maxZoom;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.maxNativeZoom;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.minNativeZoom;
/** @type {?Boolean|undefined} */
L.GridLayerOptions.prototype.noWrap;
/** @type {?string|undefined} */
L.GridLayerOptions.prototype.pane;
/** @type {?string|undefined} */
L.GridLayerOptions.prototype.className;
/** @type {?number|undefined} */
L.GridLayerOptions.prototype.keepBuffer;

/**
 * @returns {L.GridLayer}
 */
L.GridLayer.prototype.bringToFront = function() {}
/**
 * @returns {L.GridLayer}
 */
L.GridLayer.prototype.bringToBack = function() {}
/**
 * @returns {HTMLElement}
 */
L.GridLayer.prototype.getContainer = function() {}
/**
 * @param {number} opacity
 * @returns {L.GridLayer}
 */
L.GridLayer.prototype.setOpacity = function(opacity) {}
/**
 * @param {number} zIndex
 * @returns {L.GridLayer}
 */
L.GridLayer.prototype.setZIndex = function(zIndex) {}
/**
 * @returns {Boolean}
 */
L.GridLayer.prototype.isLoading = function() {}
/**
 * @returns {L.GridLayer}
 */
L.GridLayer.prototype.redraw = function() {}
/**
 * @returns {L.Point}
 */
L.GridLayer.prototype.getTileSize = function() {}
/**
 * @param {Object} coords
 * @param {function(*)=} done
 * @returns {HTMLElement}
 */
L.GridLayer.prototype.createTile = function(coords, done) {}

/*******************************************************************************
 *                                 BASIC TYPES                                 *
 *******************************************************************************/

/**
 * @constructor
 */
L.LatLng = function() {}

/**
 * @param {number|Array<number>|{lat: number, lng: number, alt: number?}} latitude
 * @param {number=} longitude
 * @param {number=} altitude
 * @constructs L.LatLng
 */
L.latLng = function(latitude, longitude, altitude) {}

/**
 * @param {ExpandedLatLng} otherLatLng
 * @param {number=} maxMargin
 * @return {Boolean}
 */
L.LatLng.prototype.equals = function(otherLatLng, maxMargin) {}
/**
 * @returns {string}
 */
L.LatLng.prototype.toString = function() {}
/**
 * @param {ExpandedLatLng} otherLatLng
 * @returns {number}
 */
L.LatLng.prototype.distanceTo = function(otherLatLng) {}
/**
 * @returns {L.LatLng}
 */
L.LatLng.prototype.wrap = function() {}
/**
 * @param {number} sizeInMeters
 * @returns {L.LatLngBounds}
 */
L.LatLng.prototype.toBounds = function(sizeInMeters) {}

/** @type {number} */
L.LatLng.prototype.lat;
/** @type {number} */
L.LatLng.prototype.lng;
/** @type {number} */
L.LatLng.prototype.alt;

/**
 * @constructor
 */
L.LatLngBounds = function() {}
/**
 * @param {ExpandedLatLng|Array<ExpandedLatLng>} corner1
 * @param {ExpandedLatLng=} corner2
 * @constructs L.LatLngBounds
 */
L.latLngBounds = function(corner1, corner2) {};

/**
 * @param {ExpandedLatLng|ExpandedLatLngBounds} latlng
 * @returns {L.LatLngBounds}
 */
L.LatLngBounds.prototype.extend = function(latlng) {}
/**
 * For example, a ratio of 0.5 extends the bounds by 50% in each direction. Negative values will retract the bounds.
 * @param {number} bufferRatio
 * @returns {L.LatLngBounds}
 */
L.LatLngBounds.prototype.pad = function(bufferRatio) {}
/**
 * @returns {L.LatLng}
 */
L.LatLngBounds.prototype.getCenter = function() {}
/**
 * @returns {L.LatLng}
 */
L.LatLngBounds.prototype.getSouthWest = function() {}
/**
 * @returns {L.LatLng}
 */
L.LatLngBounds.prototype.getNorthEast = function() {}
/**
 * @returns {L.LatLng}
 */
L.LatLngBounds.prototype.getNorthWest = function() {}
/**
 * @returns {L.LatLng}
 */
L.LatLngBounds.prototype.getSouthEast = function() {}
/**
 * @returns {number}
 */
L.LatLngBounds.prototype.getWest = function() {}
/**
 * @returns {number}
 */
L.LatLngBounds.prototype.getSouth = function() {}
/**
 * @returns {number}
 */
L.LatLngBounds.prototype.getEast = function() {}
/**
 * @returns {number}
 */
L.LatLngBounds.prototype.getNorth = function() {}
/**
 * @param {ExpandedLatLngBounds|ExpandedLatLng} otherBounds
 * @returns {Boolean}
 */
L.LatLngBounds.prototype.contains = function(otherBounds) {}
/**
 * least one point in common.
 * @param {ExpandedLatLngBounds} otherBounds
 * @returns {Boolean}
 */
L.LatLngBounds.prototype.intersects = function(otherBounds) {}
/**
 * is an area.
 * @param {ExpandedLatLngBounds} otherBounds
 * @returns {Boolean}
 */
L.LatLngBounds.prototype.overlaps = function(otherBounds) {}
/**
 * @returns {string}
 */
L.LatLngBounds.prototype.toBBoxstring = function() {}
/**
 * @param {ExpandedLatLngBounds} otherBounds
 * @param {number=} maxMargin
 * @returns {Boolean}
 */
L.LatLngBounds.prototype.equals = function(otherBounds, maxMargin) {}
/**
 * @returns {Boolean}
 */
L.LatLngBounds.prototype.isValid = function() {}

/**
 * @constructor
 */
L.Point = function() {}

/**
 * @param {number|Array<number>|{x:number, y:number}} x
 * @param {number=} y
 * @param {Boolean=} round
 * @constructs L.Point
 */
L.point = function(x, y, round) {}

/**
 * @returns {L.Point}
 */
L.Point.prototype.clone = function() {}
/**
 * @param {ExpandedPoint} otherPoint
 * @returns {L.Point}
 */
L.Point.prototype.add = function(otherPoint) {}
/**
 * @param {ExpandedPoint} otherPoint
 * @returns {L.Point}
 */
L.Point.prototype.subtract = function(otherPoint) {}
/**
 * @param {number} num
 * @returns {L.Point}
 */
L.Point.prototype.divideBy = function(num) {}
/**
 * @param {number} num
 * @returns {L.Point}
 */
L.Point.prototype.multiplyBy = function(num) {}
/**
 * @param {ExpandedPoint} scale
 * @returns {L.Point}
 */
L.Point.prototype.scaleBy = function(scale) {}
/**
 * @param {ExpandedPoint} scale
 * @returns {L.Point}
 */
L.Point.prototype.unscaleBy = function(scale) {}
/**
 * @returns {L.Point}
 */
L.Point.prototype.round = function() {}
/**
 * @returns {L.Point}
 */
L.Point.prototype.floor = function() {}
/**
 * @returns {L.Point}
 */
L.Point.prototype.ceil = function() {}
/**
 * @returns {L.Point}
 */
L.Point.prototype.trunc = function() {}
/**
 * @param {ExpandedPoint} otherPoint
 * @returns {L.Point}
 */
L.Point.prototype.distanceTo = function(otherPoint) {}
/**
 * @param {ExpandedPoint} otherPoint
 * @returns {Boolean}
 */
L.Point.prototype.equals = function(otherPoint) {}
/**
 * @param {ExpandedPoint} otherPoint
 * @returns {Boolean}
 */
L.Point.prototype.contains = function(otherPoint) {}
/**
 * @returns {string}
 */
L.Point.prototype.toString = function() {}

/** @type {number} */
L.Point.prototype.x;
/** @type {number} */
L.Point.prototype.y;

/**
 * @constructor
 */
L.Bounds = function() {}

/**
 * @param {ExpandedPoint|Array<ExpandedPoint>}corner1
 * @param {ExpandedPoint=} corner2
 * @constructs L.Bounds
 */
L.bounds = function(corner1, corner2) {}

/**
 * @param {ExpandedPoint} point
 * @returns {L.Bounds}
 */
L.Bounds.prototype.extend = function(point) {}
/**
 * @param {Boolean=} round
 * @returns {L.Point}
 */
L.Bounds.prototype.getCenter = function(round) {}
/**
 * @returns {L.Point}
 */
L.Bounds.prototype.getBottomLeft = function() {}
/**
 * @returns {L.Point}
 */
L.Bounds.prototype.getTopRight = function() {}
/**
 * @returns {L.Point}
 */
L.Bounds.prototype.getTopLeft = function() {}
/**
 * @returns {L.Point}
 */
L.Bounds.prototype.getBottomRight = function() {}
/**
 * @returns {L.Point}
 */
L.Bounds.prototype.getSize = function() {}
/**
 * @param {L.Bounds|ExpandedPoint} otherBounds
 * @returns {Boolean}
 */
L.Bounds.prototype.contains = function(otherBounds) {}
/**
 * @param {L.Bounds} otherBounds
 * @returns {Boolean}
 */
L.Bounds.prototype.intersects = function(otherBounds) {}
/**
 * @param {L.Bounds} otherBounds
 * @returns {Boolean}
 */
L.Bounds.prototype.overlaps = function(otherBounds) {}

/** @type {L.Point} */
L.Bounds.prototype.min;
/** @type {L.Point} */
L.Bounds.prototype.max;

/**
 * @constructor
 * @extends {L.Class}
 */
L.Icon = function() {}

/**
 * @record
 */
L.IconOptions = function() {}
/** @type {(?string|undefined)} */
L.IconOptions.prototype.iconUrl;
/** @type {(?string|undefined)} */
L.IconOptions.prototype.iconRetinaUrl;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.iconSize;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.iconAnchor;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.popupAnchor;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.tooltipAnchor;
/** @type {(?string|undefined)} */
L.IconOptions.prototype.shadowUrl;
/** @type {(?string|undefined)} */
L.IconOptions.prototype.shadowRetinaUrl;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.shadowSize;
/** @type {(?L.Point|undefined)} */
L.IconOptions.prototype.shadowAnchor;
/** @type {(?string|undefined)} */
L.IconOptions.prototype.className;

/**
 * @param {L.IconOptions|Object<string, *>} options
 * @constructs L.Icon
 */
L.icon = function(options) {}

/**
 * @param {HTMLElement} oldIcon
 * @returns {HTMLElement}
 */
L.Icon.prototype.createIcon = function(oldIcon) {}
/**
 * @param {HTMLElement} oldIcon
 * @returns {HTMLElement}
 */
L.Icon.prototype.createShadow = function(oldIcon) {}

/** @type {L.Icon} */
L.Icon.Default;

/**
 * @constructor
 * @extends {L.Icon}
 */
L.DivIcon = function() {}

/**
 * @record
 * @extends {L.IconOptions}
 */
L.DivIconOptions = function() {}
/** @type {(?string|?HTMLElement|undefined)} */
L.DivIconOptions.prototype.html;
/** @type {(?L.Point|undefined)} */
L.DivIconOptions.prototype.pos;

/**
 * @param {L.DivIconOptions|Object<string, *>} options
 * @constructs L.DivIcon
 */
L.divIcon = function(options) {}

/*******************************************************************************
 *                                   CONTROLS                                  *
 *******************************************************************************/

/**
 * @constructor
 * @extends {L.Class}
 */
L.Control = function() {}
/**
 * @constructor
 * @constructs L.Control
 */
L.control = function() {}

/**
 * @record
 */
L.ControlOptions = function() {}
/** @type {string} */
L.ControlOptions.prototype.position;

/**
 * @returns {string}
 */
L.Control.prototype.getPosition = function() {}
/**
 * @param {string} position
 * @returns {L.Control}
 */
L.Control.prototype.setPosition = function(position) {}
/**
 * @returns {HTMLElement}
 */
L.Control.prototype.getContainer = function() {}
/**
 * @param {L.Map} map
 * @returns {L.Control}
 */
L.Control.prototype.addTo = function(map) {}
/**
 * @returns {L.Control}
 */
L.Control.prototype.remove = function() {}
/**
 * @param {L.Map} map
 * @returns {HTMLElement}
 */
L.Control.prototype.onAdd = function(map) {}
/**
 * @param {L.Map} map
 */
L.Control.prototype.onRemove = function(map) {}

/**
 * @constructor
 * @extends {L.Control}
 */
L.ControlZoom = function() {}

/**
 * @param {(L.ControlZoomOptions|Object<string, *>)=} options
 * @constructs L.ControlZoom
 */
L.control.zoom = function(options) {}

/**
 * @record
 * @extends {L.ControlOptions}
 */
L.ControlZoomOptions = function () {}
/** @type {?string|undefined} */
L.ControlZoomOptions.prototype.zoomInText;
/** @type {?string|undefined} */
L.ControlZoomOptions.prototype.zoomInTitle;
/** @type {?string|undefined} */
L.ControlZoomOptions.prototype.zoomOutText;
/** @type {?string|undefined} */
L.ControlZoomOptions.prototype.zoomOutTitle;

/**
 * @constructor
 * @extends {L.Control}
 */
L.ControlAttribution = function() {}

/**
 * @param {(L.ControlAttributionOptions|Object<string, *>)=} options
 * @constructs L.ControlAttribution
 */
L.control.attribution = function(options) {}

/**
 * @record
 * @extends {L.ControlOptions}
 */
L.ControlAttributionOptions = function() {}
/** @type {?string|undefined} */
L.ControlAttributionOptions.prototype.prefix;

/**
 * @param {string} prefix
 * @returns {L.ControlAttribution}
 */
L.ControlAttribution.prototype.setPrefix = function(prefix) {}
/**
 * @param {string} text
 * @returns {L.ControlAttribution}
 */
L.ControlAttribution.prototype.addAttribution = function(text) {}
/**
 * @param {string} text
 * @returns {L.ControlAttribution}
 */
L.ControlAttribution.prototype.removeAttribution = function(text) {}

/**
 * @constructor
 * @extends {L.Control}
 */
L.ControlLayers = function() {}

/**
 * @param {Object=} baselayers
 * @param {Object=} overlays
 * @param {(L.ControlLayersOptions|Object<string, *>)=} options
 * @constructs L.ControlLayers
 */
L.control.layers = function(baselayers, overlays, options) {}

/**
 * @record
 * @extends {L.ControlOptions}
 */
L.ControlLayersOptions = function() {}
/** @type {?Boolean|undefined} */
L.ControlLayersOptions.prototype.collapsed;
/** @type {?Boolean|undefined} */
L.ControlLayersOptions.prototype.autoZIndex;
/** @type {?Boolean|undefined} */
L.ControlLayersOptions.prototype.hideSingleBase;
/** @type {?Boolean|undefined} */
L.ControlLayersOptions.prototype.sortLayers;
/** @type {?Function|undefined} */
L.ControlLayersOptions.prototype.sortFunction;

/**
 * @param {L.Layer} layer
 * @param {string} name
 * @returns {L.ControlLayers}
 */
L.ControlLayers.prototype.addBaseLayer = function(layer, name) {}
/**
 * @param {L.Layer} layer
 * @param {string} name
 * @returns {L.ControlLayers}
 */
L.ControlLayers.prototype.addOverlay = function(layer, name) {}
/**
 * @param {L.Layer} layer
 * @returns {L.ControlLayers}
 */
L.ControlLayers.prototype.removeLayer = function(layer) {}
/**
 * @returns {L.ControlLayers}
 */
L.ControlLayers.prototype.expand = function() {}
/**
 * @returns {L.ControlLayers}
 */
L.ControlLayers.prototype.collapse = function() {}

/**
 * @constructor
 * @extends {L.Control}
 */
L.ControlScale = function() {}

/**
 * @param {(L.ControlScaleOptions|Object<string, *>)=} options
 * @constructs L.ControlScale
 */
L.control.scale = function(options) {}

/**
 * @record
 * @extends {L.ControlOptions}
 */
L.ControlScaleOptions = function() {}
/** @type {?number|undefined} */
L.ControlScaleOptions.prototype.maxWidth;
/** @type {?Boolean|undefined} */
L.ControlScaleOptions.prototype.metric;
/** @type {?Boolean|undefined} */
L.ControlScaleOptions.prototype.imperial;
/** @type {?Boolean|undefined} */
L.ControlScaleOptions.prototype.updateWhenIdle;


/*******************************************************************************
 *                                   UTILITY                                   *
 *******************************************************************************/

/**
 * @record
 */
L.Browser = function() {}

/** @type {Boolean} */
L.Browser.ie;
/** @type {Boolean} */
L.Browser.ielt9;
/** @type {Boolean} */
L.Browser.edge;
/** @type {Boolean} */
L.Browser.webkit;
/** @type {Boolean} */
L.Browser.android;
/** @type {Boolean} */
L.Browser.android23;
/** @type {Boolean} */
L.Browser.androidStock;
/** @type {Boolean} */
L.Browser.opera;
/** @type {Boolean} */
L.Browser.chrome;
/** @type {Boolean} */
L.Browser.gecko;
/** @type {Boolean} */
L.Browser.safari;
/** @type {Boolean} */
L.Browser.opera12;
/** @type {Boolean} */
L.Browser.win;
/** @type {Boolean} */
L.Browser.ie3d;
/** @type {Boolean} */
L.Browser.webkit3d;
/** @type {Boolean} */
L.Browser.gecko3d;
/** @type {Boolean} */
L.Browser.any3d;
/** @type {Boolean} */
L.Browser.mobile;
/** @type {Boolean} */
L.Browser.mobileWebkit;
/** @type {Boolean} */
L.Browser.mobileWebkit3d;
/** @type {Boolean} */
L.Browser.msPointer;
/** @type {Boolean} */
L.Browser.pointer;
/** @type {Boolean} */
L.Browser.touch;
/** @type {Boolean} */
L.Browser.mobileOpera;
/** @type {Boolean} */
L.Browser.mobileGecko;
/** @type {Boolean} */
L.Browser.retina;
/** @type {Boolean} */
L.Browser.passiveEvents;
/** @type {Boolean} */
L.Browser.canvas;
/** @type {Boolean} */
L.Browser.svg;
/** @type {Boolean} */
L.Browser.vml;

/**
 * @constructor
 */
L.Util = function() {}

/**
 * @param {Object} dest
 * @param {Object=} src
 * @returns {Object}
 */
L.Util.extend = function(dest, src) {}
L.extend = L.Util.extend;
/**
 * @param {Object} proto
 * @param {Object=} properties
 * @returns {Object}
 */
L.Util.create = function(proto, properties) {}
/**
 * @alias L.bind
 * @param {Function} fn
 * @param {...*} args
 * @returns {Function}
 */
L.Util.bind = function(fn, ...args) {}
/**
 * @param {Object} obj
 * @returns {number}
 */
L.Util.stamp = function (obj) {}
/**
 * @alias L.throttle
 * @param {Function} fn
 * @param {number} time
 * @param {Object} context
 * @returns {Function}
 */
L.Util.throttle = function (fn, time, context) {}
/**
 * @param {number} num
 * @param {Array<number>} range
 * @param {Boolean=} includeMax
 * @returns {number}
 */
L.Util.wrapNum = function(num, range, includeMax) {}
/**
 * @returns {Function}
 */
L.Util.falseFn = function() {}
/**
 * @param {number} num
 * @param {number=} digits
 * @returns {number}
 */
L.Util.formatNum = function(num, digits) {}
/**
 * @param {string} str
 * @returns {string}
 */
L.Util.trim = function(str) {}
/**
 * @param {string} str
 * @returns {Array<string>}
 */
L.Util.splitWords = function(str) {}
/**
 * @alias L.setOptions
 * @param {Object} obj
 * @param {Object} options
 * @returns {Object}
 */
L.Util.setOptions = function(obj, options) {}
/**
 * @param {Object} obj
 * @param {string=} existingUrl
 * @param {Boolean=} uppercase
 * @returns {string}
 */
L.Util.getParamstring = function(obj, existingUrl, uppercase) {}
/**
 * @param {string} str
 * @param {Object} data
 * @returns {string}
 */
L.Util.template = function(str, data) {}
/**
 * @param {*} obj
 * @returns {Boolean}
 */
L.Util.isArray = function(obj) {}
/**
 * @param {Array} array
 * @param {Object} el
 * @returns {number}
 */
L.Util.indexOf = function(array, el) {}
/**
 * @param {Function} fn
 * @param {Object=} context
 * @param {Boolean=} immediate
 * @returns {number}
 */
L.Util.requestAnimFrame = function(fn, context, immediate) {}
/**
 * @param {number} id
 */
L.Util.cancelAnimFrame = function(id) {}

/** @type {number} */
L.Util.lastId;
/** @type {string} */
L.Util.emptyImageUrl;

/**
 * @constructor
 */
L.Transformation = function() {}

/**
 * @param {number|Array} a
 * @param {number=} b
 * @param {number=} c
 * @param {number=} d
 * @constructs L.Transformation
 */
L.transformation = function(a, b, c, d) {}

/**
 * @param {ExpandedPoint} point
 * @param {number=} scale
 * @returns {L.Point}
 */
L.Transformation.prototype.transform = function(point, scale) {}
/**
 * @param {ExpandedPoint} point
 * @param {number=} scale
 * @returns {L.Point}
 */
L.Transformation.prototype.untransform = function(point, scale) {}

/**
 * @constructor
 */
L.LineUtil = function() {}

/**
 * @param {Array<ExpandedPoint>} points
 * @param {number} tolerance
 * @returns {Array<L.Point>}
 */
L.LineUtil.simplify = function(points, tolerance) {}
/**
 * @param {ExpandedPoint} p
 * @param {ExpandedPoint} p1
 * @param {ExpandedPoint} p2
 * @returns {number}
 */
L.LineUtil.pointToSegmentDistance = function(p, p1, p2) {}
/**
 * @param {ExpandedPoint} p
 * @param {ExpandedPoint} p1
 * @param {ExpandedPoint} p2
 * @returns {number}
 */
L.LineUtil.closestPointOnSegment = function(p, p1, p2) {}
/**
 * @param {ExpandedPoint} a
 * @param {ExpandedPoint} b
 * @param {L.Bounds} bounds
 * @param {Boolean=} useLastCode
 * @param {Boolean=} round
 * @returns {Array<L.Point>|Boolean}
 */
L.LineUtil.clipSegment = function(a, b, bounds, useLastCode, round) {}
/**
 * @param {Array<ExpandedLatLng>} latlngs
 * @returns {Boolean}
 */
L.LineUtil.isFlat = function(latlngs) {}

/**
 * @constructor
 */
L.PolyUtil = function() {}

/**
 * @param {Array<ExpandedPoint>} points
 * @param {L.Bounds} bounds
 * @param {Boolean=} round
 * @returns {Array<L.Point>}
 */
L.PolyUtil.clipPolygon = function(points, bounds, round) {}

/*******************************************************************************
 *                                 DOM UTILITY                                 *
 *******************************************************************************/

/**
 * @constructor
 */
L.DomEvent = function() {}

/**
 * @alias L.DomEvent.addListener
 * @param {HTMLElement} el
 * @param {string|Object} types
 * @param {(Function|Object)=} fn
 * @param {Object=} context
 * @returns {L.DomEvent}
 */
L.DomEvent.on = function(el, types, fn, context) {}
/**
 * @alias L.DomEvent.removeListener
 * @param {HTMLElement} el
 * @param {string|Object} types
 * @param {(Function|Object)=} fn
 * @param {Object=} context
 * @returns {L.DomEvent}
 */
L.DomEvent.off = function(el, types, fn, context) {}
/**
 * @param {Event} ev
 * @returns {L.DomEvent}
 */
L.DomEvent.stopPropagation = function(ev) {}
/**
 * @param {HTMLElement} ev
 * @returns {L.DomEvent}
 */
L.DomEvent.disableScrollPropagation = function(ev) {}
/**
 * @param {HTMLElement} ev
 * @returns {L.DomEvent}
 */
L.DomEvent.disableClickPropagation = function(ev) {}
/**
 * @param {Event} ev
 * @returns {L.DomEvent}
 */
L.DomEvent.preventDefault = function(ev) {}
/**
 * @param {Event} ev
 * @returns {L.DomEvent}
 */
L.DomEvent.stop = function(ev) {}
/**
 * @param {MouseEvent} ev
 * @param {HTMLElement=} container
 * @returns {L.Point}
 */
L.DomEvent.getMousePosition = function(ev, container) {}
/**
 * @param {WheelEvent} ev
 * @returns {number}
 */
L.DomEvent.getWheelData = function(ev) {}

/**
 * @constructor
 */
L.DomUtil = function() {}

/**
 * @param {string|HTMLElement} id
 * @returns {HTMLElement}
 */
L.DomUtil.get = function(id) {}
/**
 * @param {HTMLElement} el
 * @param {string} styleAttrib
 * @returns {string}
 */
L.DomUtil.getStyle = function(el, styleAttrib) {}
/**
 * @param {string} tagName
 * @param {string=} className
 * @param {HTMLElement=} container
 * @returns {HTMLElement}
 */
L.DomUtil.create = function(tagName, className, container) {}
/**
 * @param {HTMLElement} el
 */
L.DomUtil.remove = function(el) {}
/**
 * @param {HTMLElement} el
 */
L.DomUtil.empty = function(el) {}
/**
 * @param {HTMLElement} el
 */
L.DomUtil.toFront = function(el) {}
/**
 * @param {HTMLElement} el
 */
L.DomUtil.toBack = function(el) {}
/**
 * @param {HTMLElement} el
 * @param {string} name
 * @returns {Boolean}
 */
L.DomUtil.hasClass = function(el, name) {}
/**
 * @param {HTMLElement} el
 * @param {string} name
 */
L.DomUtil.addClass = function(el, name) {}
/**
 * @param {HTMLElement} el
 * @param {string} name
 */
L.DomUtil.removeClass = function(el, name) {}
/**
 * @param {HTMLElement} el
 * @param {string} name
 */
L.DomUtil.setClass = function(el, name) {}
/**
 * @param {HTMLElement} el
 * @returns {string}
 */
L.DomUtil.getClass = function(el) {}
/**
 * @param {HTMLElement} el
 * @param {number} opacity
 */
L.DomUtil.setOpacity = function(el, opacity) {}
/**
 * @param {Array<string>} props
 * @returns {string|Boolean}
 */
L.DomUtil.testProp = function(props) {}
/**
 * @param {HTMLElement} el
 * @param {ExpandedPoint} offset
 * @param {number=} scale
 */
L.DomUtil.setTransform = function(el, offset, scale) {}
/**
 * @param {HTMLElement} el
 * @param {ExpandedPoint} position
 */
L.DomUtil.setPosition = function(el, position) {}
/**
 * @param {HTMLElement} el
 * @returns {L.Point}
 */
L.DomUtil.getPosition = function(el) {}
L.DomUtil.disableTextSelection = function() {}
L.DomUtil.enableTextSelection = function() {}
L.DomUtil.disableImageDrag = function() {}
L.DomUtil.enableImageDrag = function() {}
/**
 * @param {HTMLElement} el
 */
L.DomUtil.preventOutline = function(el) {}
L.DomUtil.restoreOutline = function() {}
/**
 * @param {HTMLElement} el
 * @returns {HTMLElement}
 */
L.DomUtil.getSizedParentNode = function(el) {}
/**
 * @param {HTMLElement} el
 * @returns {Object}
 */
L.DomUtil.getScale = function(el) {}

/** @type {string} */
L.DomUtil.TRANSFORM;
/** @type {string} */
L.DomUtil.TRANSITION;
/** @type {string} */
L.DomUtil.TRANSITION_END;

/**
 * @constructor
 * @extends {L.Evented}
 */
L.PosAnimation = function() {}

/**
 * @param {HTMLElement} el
 * @param {ExpandedPoint} newPos
 * @param {number=} duration
 * @param {number=} easeLinearity
 */
L.PosAnimation.prototype.run = function(el, newPos, duration, easeLinearity) {}
L.PosAnimation.prototype.stop = function() {}

/**
 * @param {HTMLElement} el
 * @param {HTMLElement=} dragHandle
 * @param {Boolean=} preventOutline
 * @param {(L.DraggableOptions|Object<string, *>)=} options
 * @constructor
 * @extends {L.Evented}
 */
L.Draggable = function(el, dragHandle, preventOutline, options) {}

/**
 * @record
 */
L.DraggableOptions = function() {}

/** @type {?number|undefined} */
L.DraggableOptions.prototype.clickTolerance;

L.Draggable.prototype.enable = function() {}
L.Draggable.prototype.disable = function() {}

/*******************************************************************************
 *                                 BASE CLASSES                                *
 *******************************************************************************/

/**
 * @constructor
 */
L.Class = function() {}

/**
 * @param {Object} props
 * @returns {function(...*)}
 */
L.Class.prototype.extend = function(props) {}
/**
 * @param {Object} properties
 * @returns {L.Class}
 */
L.Class.prototype.include = function(properties) {}
/**
 * @param {Object} properties
 * @returns {L.Class}
 */
L.Class.prototype.mergeOptions = function(properties) {}
/**
 * @param {function(...*)} fn
 * @returns {L.Class}
 */
L.Class.prototype.addInitHook = function(fn) {}

/**
 * @constructor
 * @extends {L.Class}
 */
L.Evented = function() {}

/**
 * @param {string|Object} type
 * @param {function(...*)=} fn
 * @param {Object=} context
 * @returns {L.Evented}
 */
L.Evented.prototype.on = function(type, fn, context) {}
L.Evented.prototype.once = L.Evented.prototype.on;
L.Evented.prototype.addEventListener = L.Evented.prototype.on;
L.Evented.prototype.addOneTimeEventListener = L.Evented.prototype.once;
/**
 * @param {(string|Object)=} type
 * @param {function(...*)=} fn
 * @param {Object=} context
 * @returns {L.Evented}
 */
L.Evented.prototype.off = function(type, fn, context) {}
L.Evented.prototype.removeEventListener = L.Evented.prototype.off;
L.Evented.prototype.clearAllEventListeners = L.Evented.prototype.off;
/**
 * @param {string} type
 * @param {Object=} data
 * @param {Boolean=} propagate
 * @returns {L.Evented}
 */
L.Evented.prototype.fire = function(type, data, propagate) {}
L.Evented.prototype.fireEvent = L.Evented.prototype.fire;
/**
 * @param {string} type
 * @returns {Boolean}
 */
L.Evented.prototype.listens = function(type) {}
L.Evented.prototype.hasEventListeners = L.Evented.prototype.listens;
/**
 * @param {L.Evented} obj
 * @returns {L.Evented}
 */
L.Evented.prototype.addEventParent = function(obj) {}
/**
 * @param {L.Evented} obj
 * @returns {L.Evented}
 */
L.Evented.prototype.removeEventParent = function(obj) {}

/**
 * @constructor
 * @extends {L.Evented}
 */
L.Layer = function() {};

/**
 * @constructor
 */
L.LayerOptions = function() {};
/** @type {string} */
L.LayerOptions.prototype.pane;
/** @type {string} */
L.LayerOptions.prototype.attribution;

/**
 * @param {L.Map|L.LayerGroup} map
 * @returns {L.Layer}
 */
L.Layer.prototype.addTo = function(map) {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.remove = function() {}
/**
 * @param {L.Map|L.LayerGroup} map
 * @returns {L.Layer}
 */
L.Layer.prototype.removeFrom = function(map) {}
/**
 * @param {string=} name
 * @returns {HTMLElement}
 */
L.Layer.prototype.getPane = function(name) {}
/**
 * @returns {string}
 */
L.Layer.prototype.getAttribution = function() {}
/**
 * @param {L.Map} map
 * @returns {L.Layer}
 */
L.Layer.prototype.onAdd = function(map) {}
/**
 * @param {L.Map} map
 * @returns {L.Layer}
 */
L.Layer.prototype.onRemove = function(map) {}
/**
 * @returns {Object}
 */
L.Layer.prototype.getEvents = function() {}
/**
 * @param {L.Map} map
 * @returns {L.Layer}
 */
L.Layer.prototype.beforeAdd = function(map) {}
/**
 * @param {string|HTMLElement|Function|L.Popup} content
 * @param {(L.PopupOptions|Object<string, *>)=} options
 * @returns {L.Layer}
 */
L.Layer.prototype.bindPopup = function(content, options) {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.unbindPopup = function() {}
/**
 * @param {ExpandedLatLng=} latlng
 * @returns {L.Layer}
 */
L.Layer.prototype.openPopup = function(latlng) {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.closePopup = function() {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.togglePopup = function() {}
/**
 * @returns {Boolean}
 */
L.Layer.prototype.isPopupOpen = function() {}
/**
 * @param {string|HTMLElement|Function|L.Popup} content
 * @returns {L.Layer}
 */
L.Layer.prototype.setPopupContent = function(content) {}
/**
 * @returns {L.Popup}
 */
L.Layer.prototype.getPopup = function() {}
/**
 * @param {string|HTMLElement|Function|L.Tooltip} content
 * @param {L.TooltipOptions=} options
 * @returns {L.Layer}
 */
L.Layer.prototype.bindTooltip = function(content, options) {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.unbindTooltip = function() {}
/**
 * @param {ExpandedLatLng=} latlng
 * @returns {L.Layer}
 */
L.Layer.prototype.openTooltip = function(latlng) {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.closeTooltip = function() {}
/**
 * @returns {L.Layer}
 */
L.Layer.prototype.toggleTooltip = function() {}
/**
 * @returns {Boolean}
 */
L.Layer.prototype.isTooltipOpen = function() {}
/**
 * @param {string|HTMLElement|Function|L.Tooltip} content
 * @returns {L.Layer}
 */
L.Layer.prototype.setTooltipContent = function(content) {}
/**
 * @returns {L.Tooltip}
 */
L.Layer.prototype.getTooltip = function() {}

/**
 * @constructor
 * @extends {L.Layer}
 */
L.InteractiveLayer = function() {}

/**
 * @constructor
 * @extends {L.LayerOptions}
 */
L.InteractiveLayerOptions = function() {}
/** @type {Boolean} */
L.InteractiveLayerOptions.prototype.interactive;
/** @type {Boolean} */
L.InteractiveLayerOptions.prototype.bubblingMouseEvents;

/**
 * @constructor
 * @extends {L.Class}
 */
L.Handler = function() {}

/**
 * @returns {L.Handler}
 */
L.Handler.prototype.enable = function() {}
/**
 * @returns {L.Handler}
 */
L.Handler.prototype.disable = function() {}
/**
 * @returns {Boolean}
 */
L.Handler.prototype.enabled = function() {}
L.Handler.prototype.addHooks = function() {}
L.Handler.prototype.removeHooks = function() {}
/**
 * @param {L.Map} map
 * @param {string} name
 * @returns {L.Handler}
 */
L.Handler.addTo = function(map, name) {}

/**
 * @constructor
 * @extends {L.Class}
 */
L.Projection = function() {}

/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Point}
 */
L.Projection.prototype.project = function(latlng) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.LatLng}
 */
L.Projection.prototype.unproject = function(point) {}

/** @type {L.Bounds} */
L.Projection.prototype.bounds;

/** @type {L.Projection} */
L.Projection.LonLat;
/** @type {L.Projection} */
L.Projection.Mercator;
/** @type {L.Projection} */
L.Projection.SphericalMercator;

/**
 * @constructor
 */
L.CRS = function() {}

/**
 * @param {ExpandedLatLng} latlng
 * @param {number} zoom
 * @returns {L.Point}
 */
L.CRS.prototype.latLngToPoint = function(latlng, zoom) {}
/**
 * @param {ExpandedPoint} point
 * @param {number} zoom
 * @returns {L.LatLng}
 */
L.CRS.prototype.pointToLatLng = function(point, zoom) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.Point}
 */
L.CRS.prototype.project = function(latlng) {}
/**
 * @param {ExpandedPoint} point
 * @returns {L.LatLng}
 */
L.CRS.prototype.unproject = function(point) {}
/**
 * @param {number} zoom
 * @returns {number}
 */
L.CRS.prototype.scale = function(zoom) {}
/**
 * @param {number} scale
 * @returns {number}
 */
L.CRS.prototype.zoom = function(scale) {}
/**
 * @param {number} zoom
 * @returns {L.Bounds}
 */
L.CRS.prototype.getProjectedBounds = function(zoom) {}
/**
 * @param {ExpandedLatLng} latlng1
 * @param {ExpandedLatLng} latlng2
 * @returns {number}
 */
L.CRS.prototype.distance = function(latlng1, latlng2) {}
/**
 * @param {ExpandedLatLng} latlng
 * @returns {L.LatLng}
 */
L.CRS.prototype.wrapLatLng = function(latlng) {}
/**
 * @param {ExpandedLatLngBounds} bounds
 * @returns {L.LatLngBounds}
 */
L.CRS.prototype.wrapLatLngBounds = function(bounds) {}

/** @type {string} */
L.CRS.code;
/** @type {Array<number>} */
L.CRS.wrapLng;
/** @type {Array<number>} */
L.CRS.wrapLat;
/** @type {Boolean} */
L.CRS.infinite;

/** @type {L.CRS} */
L.CRS.EPSG3395;
/** @type {L.CRS} */
L.CRS.EPSG3857;
/** @type {L.CRS} */
L.CRS.EPSG4326;
/** @type {L.CRS} */
L.CRS.Earth;
/** @type {L.CRS} */
L.CRS.Simple;
/** @type {L.CRS} */
L.CRS.Base;

/**
 * @constructor
 * @extends {L.Layer}
 */
L.Renderer = function() {}

/**
 * @record
 */
L.RendererOptions = function() {}
/** @type {number} */
L.RendererOptions.prototype.padding;
/** @type {number} */
L.RendererOptions.prototype.tolerance;

/*******************************************************************************
 *                                     MISC                                    *
 *******************************************************************************/

/**
 * @constructor
 */
L.Event = function() {};
/** @type {string} */
L.Event.prototype.type;
/** @type {Object} */
L.Event.prototype.target;
/** @type {Object} */
L.Event.prototype.sourceTarget;
/** @type {Object} */
L.Event.prototype.propagatedFrom;
/** @type {Object} */
L.Event.prototype.layer;

/**
 * @constructor
 * @extends {L.Event}
 */
L.KeyboardEvent = function() {}
/** @type {Event} */
L.KeyboardEvent.prototype.originalEvent;

/**
 * @constructor
 * @extends {L.Event}
 */
L.MouseEvent = function() {}
/** @type {L.LatLng} */
L.MouseEvent.prototype.latlng;
/** @type {L.Point} */
L.MouseEvent.prototype.layerPoint;
/** @type {L.Point} */
L.MouseEvent.prototype.containerPoint;
/** @type {Event} */
L.MouseEvent.prototype.originalEvent;

/**
 * @constructor
 * @extends {L.Event}
 */
L.LocationEvent = function() {}
/** @type {L.LatLng} */
L.LocationEvent.prototype.latlng;
/** @type {L.LatLngBounds} */
L.LocationEvent.prototype.bounds;
/** @type {number} */
L.LocationEvent.prototype.accuracy;
/** @type {number} */
L.LocationEvent.prototype.altitude;
/** @type {number} */
L.LocationEvent.prototype.altitudeAccuracy;
/** @type {number} */
L.LocationEvent.prototype.heading;
/** @type {number} */
L.LocationEvent.prototype.speed;
/** @type {number} */
L.LocationEvent.prototype.timestamp;

/**
 * @constructor
 * @extends {L.Event}
 */
L.ErrorEvent = function() {}
/** @type {string} */
L.ErrorEvent.prototype.message;
/** @type {number} */
L.ErrorEvent.prototype.code;

/**
 * @constructor
 * @extends {L.Event}
 */
L.LayerEvent = function() {}
/** @type {L.Layer} */
L.LayerEvent.prototype.layer;

/**
 * @constructor
 * @extends {L.Event}
 */
L.LayersControlEvent = function() {}
/** @type {L.Layer} */
L.LayersControlEvent.prototype.layer;
/** @type {string} */
L.LayersControlEvent.prototype.name;

/**
 * @constructor
 * @extends {L.Event}
 */
L.TileEvent = function() {}
/** @type {HTMLElement} */
L.TileEvent.prototype.tile;
/** @type {L.Point} */
L.TileEvent.prototype.coords;

/**
 * @constructor
 * @extends {L.Event}
 */
L.TileErrorEvent = function() {}
/** @type {HTMLElement} */
L.TileErrorEvent.prototype.tile;
/** @type {L.Point} */
L.TileErrorEvent.prototype.coords;
/** @type {*} */
L.TileErrorEvent.prototype.error;

/**
 * @constructor
 * @extends {L.Event}
 */
L.ResizeEvent = function() {}
/** @type {L.Point} */
L.ResizeEvent.prototype.oldSize;
/** @type {L.Point} */
L.ResizeEvent.prototype.newSize;

/**
 * @constructor
 * @extends {L.Event}
 */
L.GeoJSONEvent = function() {}
/** @type {L.Layer} */
L.GeoJSONEvent.prototype.layer;
/** @type {Object} */
L.GeoJSONEvent.prototype.properties;
/** @type {string} */
L.GeoJSONEvent.prototype.geometryType;
/** @type {string} */
L.GeoJSONEvent.prototype.id;

/**
 * @constructor
 * @extends {L.Event}
 */
L.PopupEvent = function() {}
/** @type {L.Popup} */
L.PopupEvent.prototype.popup;

/**
 * @constructor
 * @extends {L.Event}
 */
L.TooltipEvent = function() {}
/** @type {L.Tooltip} */
L.TooltipEvent.prototype.tooltip;

/**
 * @constructor
 * @extends {L.Event}
 */
L.DragEndEvent = function() {}
/** @type {number} */
L.DragEndEvent.prototype.distance;

/**
 * @constructor
 * @extends {L.Event}
 */
L.ZoomAnimEvent = function() {}
/** @type {L.LatLng} */
L.ZoomAnimEvent.prototype.center;
/** @type {number} */
L.ZoomAnimEvent.prototype.zoom;
/** @type {Boolean} */
L.ZoomAnimEvent.prototype.noUpdate;

/**
 * @constructor
 * @extends {L.Layer}
 */
L.DivOverlay = function() {}

/**
 * @constructor
 * @extends {L.LayerOptions}
 */
L.DivOverlayOptions = function() {}
/** @type {?L.Point|undefined} */
L.DivIconOptions.prototype.offset;
/** @type {?string|undefined} */
L.DivIconOptions.prototype.className;
/** @type {?string|undefined} */
L.DivIconOptions.prototype.pane;

/**
 * @returns {L}
 */
L.noConflict = function() {}

/** @type {string} */
L.version;