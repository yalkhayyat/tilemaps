from config import *
from rbx_open_cloud import AssetType, ContentType
from mapbox import *
import argparse, subprocess
import bpy
from PIL import Image
import numpy as np
from scipy.ndimage import zoom
import matplotlib.pyplot as plt
import json
import math
import mercantile

bpy.app.binary_path = BLENDER_PATH


def UploadTileMesh(x, y, z):
    MAPBOX.GetImageTile(
        MapboxAPI.Tilesets.TERRAIN_DEM, x, y, z, ".pngraw", SAVED_HEIGHTMAP_PATH
    )
    GetHeightmappedMesh(x, y, z, SAVED_HEIGHTMAP_PATH, SAVED_MESH_PATH, True)
    op_id = ROBLOX.CreateAsset(
        SAVED_MESH_PATH,
        AssetType.MESH,
        ContentType.FBX,
        display_name=f"TILE_{x}_{y}_{z}",
    )

    return op_id


def UploadFlatTileMesh(x, y, z):
    MAPBOX.GetImageTile(
        MapboxAPI.Tilesets.TERRAIN_DEM, x, y, z, ".pngraw", SAVED_HEIGHTMAP_PATH
    )
    GetHeightmappedMesh(x, y, z, SAVED_HEIGHTMAP_PATH, SAVED_MESH_PATH, False)
    op_id = ROBLOX.CreateAsset(
        SAVED_MESH_PATH,
        AssetType.MESH,
        ContentType.FBX,
        display_name=f"TILE_{x}_{y}_{z}",
    )

    print(op_id)

    return op_id


def SaveTileToJSON(x, y, z, value, output_file):
    try:
        with open(output_file, "r") as f:
            keys = json.load(f)
    except FileNotFoundError:
        keys = {}
    except json.JSONDecodeError:
        keys = {}

    keys[f"{x}_{y}_{z}"] = value

    with open(output_file, "w") as f:
        json.dump(keys, f, indent=4)


# Function to convert Mercator x, y to spherical coordinates
def mercator_to_sphere(latitude, longitude, radius):
    X = radius * math.cos(math.radians(latitude)) * math.cos(math.radians(longitude))
    Y = radius * math.cos(math.radians(latitude)) * math.sin(math.radians(longitude))
    Z = radius * math.sin(math.radians(latitude))

    return X, Y, Z


def GetHeightmappedMesh(x, y, z, heightmap_path, output_path, spherical):
    bpy.ops.wm.open_mainfile(filepath=BLENDER_TILE_PATH)
    tile = bpy.context.scene.objects[0]

    with Image.open(heightmap_path) as img:
        img = img.convert("RGB")
        img_array = np.array(img, dtype=np.int32)

        # RGB to height conversion
        coeff = np.array([256 * 256, 256, 1], dtype=np.float32)
        height_map_2d = -10000 + (np.tensordot(img_array, coeff, axes=([2], [0])) * 0.1)
        height_map_2d = np.clip(height_map_2d, a_min=0, a_max=None)

        # Resize height_map_2d to 32x32 to match mesh vertices
        resized_height_map = zoom(
            height_map_2d,
            (
                TILE_VERTEX_LENGTH / height_map_2d.shape[0],
                TILE_VERTEX_LENGTH / height_map_2d.shape[1],
            ),
        )

        mesh = tile.data
        # max_height = 0

        # Apply heights to mesh vertices
        for i, vertex in enumerate(mesh.vertices):
            # get pixel idx
            x_idx = int(np.round(vertex.co.x * (TILE_VERTEX_LENGTH - 1)))
            y_idx = int(np.round((1 - vertex.co.y) * (TILE_VERTEX_LENGTH - 1)))

            # get height value
            height = resized_height_map[y_idx, x_idx]

            if spherical:
                # get longitude
                n = 1 << z
                lon_deg = (x + vertex.co.x) / n * 360.0 - 180.0

                # get latitude
                lat_rad = math.atan(
                    math.sinh(math.pi * (1 - 2 * (y + 1 - vertex.co.y) / n))
                )
                lat_deg = math.degrees(lat_rad)

                r = 6378137
                if vertex.co.z > 0:
                    r += height

                # get spherical
                x_s, y_s, z_s = mercator_to_sphere(
                    lat_deg, lon_deg, r * 0.0001 * 0.01  # small scale + 0.01 fbx units
                )

                # assign position
                vertex.co.x = x_s
                vertex.co.y = y_s
                vertex.co.z = z_s
            else:
                vertex.co.z = height / (40075000 / 2**z)

            # max_height = max(max_height, height)

    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    SaveTileToJSON(
        x,
        y,
        z,
        f"{tile.location.x}_{tile.location.y}_{tile.location.z}",
        MESH_VERT_OFFSET_PATH,
    )

    bpy.ops.export_scene.fbx(filepath=output_path)


if __name__ == "__main__":
    # UploadTileMesh(536, 358, 10)
    # UploadTileMesh(535, 358, 10)
    UploadTileMesh(19, 46, 7)
    # UploadTileMesh(38, 91, 8)
