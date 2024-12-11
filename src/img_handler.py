from config import *
from img_utils import extend_image_edges
from rbx_open_cloud import AssetType, ContentType
from mapbox import *


def UploadTileImg(x, y, z):
    MAPBOX.GetImageTile(MapboxAPI.Tilesets.SATELLITE, x, y, z, ".jpg", SAVED_IMG_PATH)
    # SENTINEL.get_image_tile(x, y, z, SAVED_IMG_PATH)
    extend_image_edges(SAVED_IMG_PATH, 16)
    op_id = ROBLOX.CreateAsset(
        SAVED_IMG_PATH,
        AssetType.IMAGE,
        ContentType.JPEG,
        display_name=f"TILE_{x}_{y}_{z}",
    )

    return op_id


if __name__ == "__main__":
    UploadTileImg(544, 358, 10)
