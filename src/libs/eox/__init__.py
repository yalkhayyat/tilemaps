from .eox_constants import *
import requests


class GetImageTileFailedException(Exception):
    def __init__(self, x, y, z) -> None:
        super().__init__(f"Failed to get image tile at: X:{x} Y:{y} ZOOM:{z}")


class EOXClient:
    def __init__(self, max_retries) -> None:
        self.max_retries = max_retries

    def GetImageTile(self, tileset_id, x, y, z, file_format, output_path):
        url = EOXAPI.RASTER_API.format(z, y, x)

        for i in range(self.max_retries):
            response = requests.get(url, timeout=60)

            if response.status_code // 100 == 2:
                # Save the map tile to file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                    f.close()
                    return

        raise GetImageTileFailedException(x, y, z)
