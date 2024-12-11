import os
import rasterio
import numpy as np
import pyproj
from sentinelsat import SentinelAPI
from rasterio.windows import Window
from rasterio.transform import from_origin
from rasterio.warp import calculate_default_transform, reproject, Resampling
from typing import Tuple, List


class GetImageTileFailedException(Exception):
    def __init__(self, x: int, y: int, z: int, message: str = None) -> None:
        error_msg = f"Failed to get image tile at: X:{x} Y:{y} ZOOM:{z}"
        if message:
            error_msg += f" - {message}"
        super().__init__(error_msg)


class CopernicusTileClient:
    def __init__(
        self,
        username: str,
        password: str,
        max_retries: int = 3,
    ):
        """
        Initialize Copernicus Hub client for retrieving satellite tiles in Web Mercator

        :param username: Copernicus Hub username
        :param password: Copernicus Hub password
        :param max_retries: Maximum number of download attempts
        """
        self.api = SentinelAPI(username, password)
        self.max_retries = max_retries

        # Projection transformations
        self.wgs84 = pyproj.CRS("EPSG:4326")  # WGS84 (lat/lon)
        self.web_mercator = pyproj.CRS("EPSG:3857")  # Web Mercator
        self.transformer = pyproj.Transformer.from_crs(
            self.wgs84, self.web_mercator, always_xy=True
        )

    def get_image_tile(
        self,
        x: int,
        y: int,
        z: int,
        output_path: str = None,
        date_range: Tuple[str, str] = ("20230101", "20231231"),
        max_cloud_cover: float = 10.0,
    ) -> str:
        """
        Retrieve a satellite image tile for given XYZ coordinates in Web Mercator

        :param x: Tile X coordinate
        :param y: Tile Y coordinate
        :param z: Zoom level
        :param output_path: Optional custom output path
        :param date_range: Date range for image search (start, end)
        :param max_cloud_cover: Maximum acceptable cloud cover percentage
        :param bands: Optional list of bands to extract (e.g., ['B04', 'B03', 'B02'])
        :return: Path to saved tile image
        """
        # Calculate geographic bounds for the tile
        lon_min, lat_min = self._tile_to_lonlat(x, y, z)
        lon_max, lat_max = self._tile_to_lonlat(x + 1, y + 1, z)

        # Transform bounds to Web Mercator
        merc_min_x, merc_min_y = self.transformer.transform(lon_min, lat_min)
        merc_max_x, merc_max_y = self.transformer.transform(lon_max, lat_max)

        # Create a bounding box for search
        footprint = f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},{lon_max} {lat_max},{lon_min} {lat_max},{lon_min} {lat_min}))"

        # Search for Sentinel-2 products
        products = self.api.query(
            footprint,
            # date=date_range,
            # platformname="Sentinel-2",
            # cloudcoverpercentage=(0, max_cloud_cover),
        )

        if not products:
            raise GetImageTileFailedException(x, y, z, "No suitable images found")

        # Sort products by cloud cover and acquisition date
        products_df = self.api.to_dataframe(products)
        products_df = products_df.sort_values(["cloudcoverpercentage", "beginposition"])

        selected_product = products_df.iloc[0]

        # Download the product
        download_path = self.api.download(
            selected_product.uuid, directory_path=self.download_dir
        )
        downloaded_file = download_path["path"]

        # Open the downloaded product
        with rasterio.open(downloaded_file) as src:
            bands = ["B04", "B03", "B02"]  # Red, Green, Blue

            # Extract specified bands
            band_indices = [src.descriptions.index(band) + 1 for band in bands]

            # Read the bands
            tile_data = src.read(band_indices)

            # Calculate transform for Web Mercator tile
            transform = rasterio.transform.from_bounds(
                merc_min_x, merc_min_y, merc_max_x, merc_max_y, width=512, height=512
            )

            # Prepare output profile for Web Mercator
            profile = {
                "driver": "GTiff",
                "height": 512,
                "width": 512,
                "count": len(bands),
                "dtype": tile_data.dtype,
                "crs": self.web_mercator.to_wkt(),
                "transform": transform,
                "compress": "lzw",
            }

            # Write the tile in Web Mercator
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(tile_data)

        return output_path

    def _tile_to_lonlat(self, x: int, y: int, z: int) -> Tuple[float, float]:
        """
        Convert XYZ tile coordinates to Longitude/Latitude

        :param x: Tile X coordinate
        :param y: Tile Y coordinate
        :param z: Zoom level
        :return: (longitude, latitude)
        """
        n = 2.0**z
        lon_deg = x / n * 360.0 - 180.0
        lat_deg = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * y / n))))
        return lon_deg, lat_deg
