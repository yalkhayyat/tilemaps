from src.config import *
from PIL import Image
import numpy as np
from src.libs.rbx_open_cloud import AssetType, ContentType
from src.libs.mapbox import *


def extend_image_edges(image_path, padding):
    # Open the original image and convert to a numpy array
    img = Image.open(image_path)
    img_array = np.array(img)

    # Get dimensions of the original image
    height, width = img_array.shape[:2]

    # Create a new array with padding added
    new_height, new_width = height + 2 * padding, width + 2 * padding
    new_img_array = np.zeros((new_height, new_width, 3), dtype=img_array.dtype)

    # Place the original image in the center
    new_img_array[padding : padding + height, padding : padding + width] = img_array

    # Extend edges
    # Left and right
    new_img_array[padding : padding + height, :padding] = img_array[:, 0:1]  # Left
    new_img_array[padding : padding + height, -padding:] = img_array[:, -1:]  # Right

    # Top and bottom
    new_img_array[:padding, padding : padding + width] = img_array[0:1, :]  # Top
    new_img_array[-padding:, padding : padding + width] = img_array[-1:, :]  # Bottom

    # Corners
    new_img_array[:padding, :padding] = img_array[0, 0]  # Top-left corner
    new_img_array[:padding, -padding:] = img_array[0, -1]  # Top-right corner
    new_img_array[-padding:, :padding] = img_array[-1, 0]  # Bottom-left corner
    new_img_array[-padding:, -padding:] = img_array[-1, -1]  # Bottom-right corner

    # Convert the result back to an image and save it
    new_img = Image.fromarray(new_img_array)
    new_img.save(image_path)


def UploadTileImg(x, y, z):
    IMAGERY_CLIENT.GetImageTile(MapboxAPI.Tilesets.SATELLITE, x, y, z, ".jpg", SAVED_IMG_PATH)
    extend_image_edges(SAVED_IMG_PATH, 16)
    op_id = ROBLOX.CreateAsset(
        SAVED_IMG_PATH,
        AssetType.IMAGE,
        ContentType.JPEG,
        display_name=f"TILE_{x}_{y}_{z}",
    )

    return op_id