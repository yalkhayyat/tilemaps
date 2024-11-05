from mapbox.mapbox_constants import *
import requests
from PIL import Image


class GetImageTileFailedException(Exception):
    def __init__(self, x, y, z) -> None:
        super().__init__(f"Failed to get image tile at: X:{x} Y:{y} ZOOM:{z}")


class MapboxClient:
    def __init__(self, api_key, max_retries) -> None:
        self.api_key = api_key
        self.max_retries = max_retries

    def GetImageTile(self, tileset_id, x, y, z, file_format, output_path):
        url = MapboxAPI.RASTER_API.format(
            tileset_id, z, x, y, file_format, self.api_key
        )

        for i in range(self.max_retries):
            response = requests.get(url)

            if response.status_code // 100 == 2:
                # Save the map tile to file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                    f.close()
                    return
            elif (
                "Tile not found" in response.text
                and tileset_id == MapboxAPI.Tilesets.TERRAIN_DEM
            ):
                Image.new("RGB", (512, 512), (0, 0, 0)).save(output_path)
                return

        raise GetImageTileFailedException(x, y, z)
