from mapbox.mapbox_constants import *
import requests
from PIL import Image
from io import BytesIO


class GetImageTileFailedException(Exception):
    def __init__(self, x, y, z) -> None:
        super().__init__(f"Failed to get image tile at: X:{x} Y:{y} ZOOM:{z}")


class MapboxClient:
    def __init__(self, api_key, max_retries) -> None:
        self.api_key = api_key
        self.max_retries = max_retries

    def GetImageTile(self, tileset_id, x, y, z, file_format, output_path):
        if tileset_id == MapboxAPI.Tilesets.TERRAIN_DEM and z > 14:
            requested_zoom = 14
            scale_factor = 2 ** (z - requested_zoom)
            requested_x = x // scale_factor
            requested_y = y // scale_factor
        else:
            requested_zoom = z
            scale_factor = 1
            requested_x = x
            requested_y = y

        url = MapboxAPI.RASTER_API.format(
            tileset_id,
            requested_zoom,
            requested_x,
            requested_y,
            file_format,
            self.api_key,
        )

        for i in range(self.max_retries):
            response = requests.get(url)

            if response.status_code // 100 == 2:
                # Save the map tile to file
                if scale_factor == 1:
                    with open(output_path, "wb") as f:
                        f.write(response.content)
                        f.close()
                        return
                else:
                    base_tile = Image.open(BytesIO(response.content))

                    # Calculate crop size
                    tile_size = 512  # Size of a Mapbox tile
                    crop_size = tile_size // scale_factor

                    # Calculate crop position for the x, y of the requested zoom level
                    crop_x = (x % scale_factor) * crop_size
                    crop_y = (y % scale_factor) * crop_size
                    cropped_tile = base_tile.crop(
                        (crop_x, crop_y, crop_x + crop_size, crop_y + crop_size)
                    )

                    # Resize cropped tile to standard tile size
                    resized_tile = cropped_tile.resize((tile_size, tile_size))
                    resized_tile.save(output_path)
                    return

            elif (
                "Tile not found" in response.text
                and tileset_id == MapboxAPI.Tilesets.TERRAIN_DEM
            ):
                Image.new("RGB", (512, 512), (0, 0, 0)).save(output_path)
                return

        raise GetImageTileFailedException(x, y, z)
