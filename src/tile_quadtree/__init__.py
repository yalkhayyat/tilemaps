import math


def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 1 << zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def num2deg(xtile, ytile, zoom):
    n = 1 << zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lat_deg, lon_deg


class GpsPoint:
    def __init__(self, latitude, longitude) -> None:
        self.latitude = latitude
        self.longitude = longitude


class Tile:
    def __init__(self, x, y, zoom) -> None:
        self.x = x
        self.y = y
        self.zoom = zoom
        self.children: list[Tile] = []
        self.is_leaf = True


class QuadTree:
    def __init__(self, root: Tile, max_lod, lod_subdivide_threshold) -> None:
        self.root = root
        self.max_lod = max_lod
        self.lod_subdivide_threshold = lod_subdivide_threshold
        self.gps_points: list[GpsPoint] = []

    def AddPoint(self, lat, lon):
        self.gps_points.append(GpsPoint(lat, lon))

    def __subdivide(self, tile: Tile):
        for point in self.gps_points:
            point_tile_x, point_tile_y = deg2num(
                point.latitude, point.longitude, tile.zoom
            )

            if (
                abs(point_tile_x - tile.x) <= 1 and abs(point_tile_y - tile.y) <= 1
            ) or tile.zoom >= self.lod_subdivide_threshold:
                # Subdivide
                top_left = Tile(tile.x * 2, tile.y * 2, tile.zoom + 1)
                top_right = Tile(tile.x * 2 + 1, tile.y * 2, tile.zoom + 1)
                bottom_left = Tile(tile.x * 2, tile.y * 2 + 1, tile.zoom + 1)
                bottom_right = Tile(tile.x * 2 + 1, tile.y * 2 + 1, tile.zoom + 1)

                tile.children = [
                    top_left,
                    top_right,
                    bottom_left,
                    bottom_right,
                ]

                tile.is_leaf = False

                return

    def __buildTreeRecurse(self, tile: Tile):
        if tile.zoom < self.max_lod:
            if tile.is_leaf:
                self.__subdivide(tile)

            for child in tile.children:
                self.__buildTreeRecurse(child)

    def BuildTree(self):
        self.__buildTreeRecurse(self.root)