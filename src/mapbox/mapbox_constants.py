from enum import StrEnum


class MapboxAPI:
    RASTER_API = "https://api.mapbox.com/v4/{}/{}/{}/{}@2x{}?access_token={}"

    class Tilesets:
        SATELLITE = "mapbox.satellite"
        TERRAIN_DEM = "mapbox.mapbox-terrain-dem-v1"
