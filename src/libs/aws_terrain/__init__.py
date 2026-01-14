from .aws_constants import *
import requests


class GetImageTileFailedException(Exception):
    def __init__(self, x, y, z) -> None:
        super().__init__(f"Failed to get terrain tile at: X:{x} Y:{y} ZOOM:{z}")


class AWSTerrainClient:
    def __init__(self, max_retries) -> None:
        self.max_retries = max_retries

    def GetImageTile(self, tileset_id, x, y, z, file_format, output_path):
        """
        Fetch terrain tile from AWS Terrarium.
        Note: tileset_id and file_format are ignored - AWS only serves PNG terrain tiles.
        """
        url = AWSAPI.TERRAIN_API.format(z, x, y)

        for i in range(self.max_retries):
            response = requests.get(url, timeout=60)

            if response.status_code // 100 == 2:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                    return

        raise GetImageTileFailedException(x, y, z)
