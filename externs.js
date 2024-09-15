/**
 * JavaScript definitions of "externs" for Google Closure Compiler which is used to reduce size of the output.
 * This has been manually created to fit current needs. May need to be revisited when Folium generator changes.
 * There is e.g. https://gist.github.com/PeterTillema/74117f5c7a2f2ff603b5ec5c95f83230 available which provides much wider Folium
 * coverage but it is outdated by a few years and does not work reliably.
 *
 * @externs
 */

function L() {}
L.CRS = function() {};
L.CRS.EPSG3857;

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
L.MapOptions.prototype.crs;
L.MapOptions.prototype.center;
/** @type {?number|undefined} */
L.MapOptions.prototype.zoom;
/** @type {?number|undefined} */
L.MapOptions.prototype.minZoom;
/** @type {?number|undefined} */
L.MapOptions.prototype.maxZoom;
L.MapOptions.prototype.layers;
L.MapOptions.prototype.maxBounds;
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

L.featureGroup = function(x) {};
L.tileLayer = function(x, y) {};
L.polyline = function(x, y) {};
L.polyline.addTo = function(x) {};
L.polyline.bindPopup = function(x) {};
L.popup = function() {};
L.popup.setContent = function(x) {};
L.control = function() {};
L.control.fullscreen = function(x) {};
L.control.locate = function(x) {};
L.control.layers = function(x, y, z) {};
L.Draggable = class {
        constructor(x) {
        }
        enable(){}
};
const $ = function(x) {};