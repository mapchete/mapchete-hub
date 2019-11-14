//import Map from 'ol-debug/Map.js';
//import View from 'ol-debug/View.js';
//import {defaults as defaultControls, OverviewMap} from 'ol-debug/control.js';
//import {defaults as defaultInteractions, DragRotateAndZoom} from 'ol-debug/interaction.js';
//import TileLayer from 'ol/layer/Tile.js';
//import OSM from 'ol-debug/source/OSM.js';


var init_zoom = config.init_zoom || 2;
var init_lon = config.init_lon || 0.0;
var init_lat = config.init_lat || 0.0;
var srs = config.srs || 'EPSG:4326'

if (srs == 'EPSG:4326') {
    var matrix_set = 'WGS84'
    var min_zoom = 0
    var max_zoom = 13
    var s2maps_base_overlay_layer = 'overlay_base'
    var s2maps_base_bright_overlay_layer = 'overlay'
    var s2maps_terrain_layer = 'terrain-light'
    var s2cloudless2018_layer = 's2cloudless-2018'
    var s2cloudless2016_layer = 's2cloudless'
    var dirname = "geodetic"
} else {
    var matrix_set = 'GoogleMapsCompatible'
    var min_zoom = 0
    var max_zoom = 14
    var s2maps_base_overlay_layer = 'overlay_base_3857'
    var s2maps_base_bright_overlay_layer = 'overlay_3857'
    var s2maps_terrain_layer = 'terrain-light_3857'
    var s2cloudless2018_layer = 's2cloudless-2018_3857'
    var s2cloudless2016_layer = 's2cloudless_3857'
    var dirname = "mercator"
}



// parse permalink items
var hash = (window.location.hash || '').replace('#', '');
var parts = hash.split('&');
var obj = {};
for (var i = 0; i < parts.length; ++i) {
    var kv = parts[i].split('=');
    obj[kv[0]] = kv[1];
}

zoom = parseInt(typeof obj.zoom === 'undefined' ? init_zoom : obj.zoom, 10);
center = [
    parseFloat(typeof obj.lon === 'undefined' ? init_lon : obj.lon),
    parseFloat(typeof obj.lat === 'undefined' ? init_lat : obj.lat)
];

// determine tile grid
zoomOffset = 1;
var projection = ol.proj.get(srs);
var projectionExtent = projection.getExtent();
var size = ol.extent.getHeight(projectionExtent) / 256;
var resolutions = new Array(max_zoom+zoomOffset);
var matrixIds = new Array(max_zoom+zoomOffset);
var sizes = new Array(max_zoom+zoomOffset);
// generate resolutions and matrixIds arrays for this WMTS
for (var z = min_zoom; z <= max_zoom; ++z) {
    resolutions[z] = size / Math.pow(2, z);
    matrixIds[z] = z;
}
tile_grid = new ol.tilegrid.WMTS({
    origin: ol.extent.getTopLeft(projectionExtent),
    resolutions: resolutions,
    matrixIds: matrixIds,
})
var maps_urls = [
    "//a.s2maps-tiles.eu/wmts/",
    "//b.s2maps-tiles.eu/wmts/",
    "//c.s2maps-tiles.eu/wmts/",
    "//d.s2maps-tiles.eu/wmts/",
    "//e.s2maps-tiles.eu/wmts/"
];
wmts_defaults = {
    maxZoom: max_zoom,
    matrixSet: matrix_set,
    format: 'image/jpeg',
    projection: projection,
    tileGrid: tile_grid,
    style: 'default',
    wrapX: false,
    transition: 0,
    urls: maps_urls
}
mhub_defaults = {
    projection: projection,
    requestEncoding: 'REST',
    transition: 0,
}


// EOxMaps layers
var s2maps_base_overlay = new ol.layer.Tile({
    title: 'Overlay Base',
    type: 'overlay',
    visible: false,
    source: new ol.source.WMTS({
        layer: s2maps_base_overlay_layer,
        ...wmts_defaults
    })
});
var s2maps_base_bright_overlay = new ol.layer.Tile({
    title: 'Overlay Base Bright',
    type: 'overlay',
    visible: false,
    source: new ol.source.WMTS({
        layer: s2maps_base_bright_overlay_layer,
        ...wmts_defaults
    })
});
var s2maps_terrain = new ol.layer.Tile({
    type: 'base',
    title: 'EOxMaps Terrain Light',
    source: new ol.source.WMTS({
        layer: s2maps_terrain_layer,
        ...wmts_defaults
    })
});
var s2cloudless2018 = new ol.layer.Tile({
    title: 'Sentinel-2 Cloudless 2018',
    type: 'base',
    source: new ol.source.WMTS({
        layer: s2cloudless2018_layer,
        ...wmts_defaults
    })
});
var s2cloudless2016 = new ol.layer.Tile({
    title: 'Sentinel-2 Cloudless 2016',
    type: 'base',
    source: new ol.source.WMTS({
        layer: s2cloudless2016_layer,
        ...wmts_defaults
    })
});


// mhub layers
var ndvi_wms_layer = new ol.layer.Tile({
    title: 'Sentinel-2 NDVI',
    type: 'overlay',
    source: new ol.source.TileWMS({
        attributions: '<a href="https://s2maps.eu">Sentinel-2 cloudless - https://s2maps.eu</a> by <a href="https://eox.at">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2017 & 2018)',
        url: "/mapserver?map=/map/" + dirname + "/nir.map&",
        params: {'LAYERS': 'map', 'FORMAT': 'image/tiff', 'TRANSPARENT': 'false'},
        ...mhub_defaults
    })
});
var ndwi_wms_layer = new ol.layer.Tile({
    title: 'Sentinel-2 NDWI',
    type: 'overlay',
    source: new ol.source.TileWMS({
        attributions: '<a href="https://s2maps.eu">Sentinel-2 cloudless - https://s2maps.eu</a> by <a href="https://eox.at">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2017 & 2018)',
        url: "/mapserver?map=/map/" + dirname + "/nir.map&",
        params: {'LAYERS': 'map', 'FORMAT': 'image/tiff', 'TRANSPARENT': 'false'},
        ...mhub_defaults
    })
});
var s2_false_color_infrared = new ol.layer.Tile({
    title: 'Sentinel-2 False Color Infrared',
    type: 'overlay',
    source: new ol.source.TileWMS({
      attributions: '<a href="https://s2maps.eu">Sentinel-2 cloudless - https://s2maps.eu</a> by <a href="https://eox.at">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2017 & 2018)',
      url: "/mapserver?map=/map/" + dirname + "/fcir.map&",
      params: {'LAYERS': 'map', 'FORMAT': 'image/jpeg', 'TRANSPARENT': 'false'},
      ...mhub_defaults
    })
});
var s2_true_color = new ol.layer.Tile({
    title: '8bit Color Corrected',
    type: 'overlay',
    visible: false,
    source: new ol.source.TileWMS({
        attributions: '<a href="https://s2maps.eu">Sentinel-2 cloudless - https://s2maps.eu</a> by <a href="https://eox.at">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2017 & 2018)',
        url: "/mapserver?map=/map/" + dirname + "/s2cloudless.map&",
        params: {'LAYERS': 'map', 'FORMAT': 'image/jpeg', 'TRANSPARENT': 'false'},
        ...mhub_defaults
    })
});
var s2_debug = new ol.layer.Tile({
    title: '16bit Stretched',
    type: 'overlay',
    visible: true,
    source: new ol.source.TileWMS({
        attributions: '<a href="https://s2maps.eu">Sentinel-2 cloudless - https://s2maps.eu</a> by <a href="https://eox.at">EOX IT Services GmbH</a> (Contains modified Copernicus Sentinel data 2017 & 2018)',
        url: "/mapserver?map=/map/" + dirname + "/debug.map&",
        params: {'LAYERS': 'map', 'FORMAT': 'image/jpeg', 'TRANSPARENT': 'false'},
        ...mhub_defaults
    })
 });

var map = new ol.Map({
    layers: [
        s2cloudless2016,
        s2cloudless2018,
        s2maps_terrain,
        s2_true_color,
        s2_debug,
        s2maps_base_overlay,
        s2maps_base_bright_overlay,
    ],
    target: 'map',
    controls: ol.control.defaults({
        attributionOptions: /** @type {olx.control.AttributionOptions} */ ({}),
        collapsible: true,
    }),
    view: new ol.View({
        center: center,
        zoom: zoom + zoomOffset,
        projection: srs,
        maxZoom: max_zoom + zoomOffset,
        minZoom: min_zoom + zoomOffset
    })
});
map.on('moveend', function() {
    var view = map.getView();
    var center = view.getCenter();
    window.location.hash =
    'zoom=' + (view.getZoom()-zoomOffset) + '&' + 'lon=' + center[0] + '&' + 'lat=' + center[1];
});

// setup datafunctions
var datafunctions = {};
datafunctions['NDVI'] = function(b) {
    if(b[1]+b[2]==0) return 10; // return 10 as nodata value
    return ( b[1] - b[2] ) / ( b[1] + b[2] );
};
datafunctions['NDWI'] = function(b) {
    if(b[1]+b[3]==0) return 10; // return 10 as nodata value
    return ( b[3] - b[1] ) / ( b[3] + b[1] );
};

// olGeoTiff setup
// var ndvi_map = new olGeoTiff(ndvi_wms_layer);
// ndvi_map.plotOptions.domain = [1.25, -1.0];
// ndvi_map.plotOptions.noDataValue = 10;
// ndvi_map.plotOptions.palette = 'earth';
// ndvi_map.plotOptions.dataFunction = datafunctions['NDVI'];
// ndvi_wms_layer.setOpacity(1);
// ndvi_map.redraw();


// var ndwi_map = new olGeoTiff(ndwi_wms_layer);
// ndwi_map.plotOptions.domain = [1.5, -1.5];
// ndwi_map.plotOptions.noDataValue = 10;
// ndwi_map.plotOptions.palette = 'jet';
// ndwi_map.plotOptions.dataFunction = datafunctions['NDWI'];
// ndwi_wms_layer.setOpacity(1);
// ndwi_map.redraw();



var mouse_position = new ol.control.MousePosition({
    coordinateFormat: ol.coordinate.createStringXY(5),
    projection: 'EPSG:4326'
});
map.addControl(mouse_position);


var layerSwitcher = new ol.control.LayerSwitcher({
    tipLabel: 'EOX Sentinel-2 Layers' // Optional label
});;
map.addControl(layerSwitcher);
