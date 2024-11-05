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

bpy.app.binary_path = BLENDER_PATH


def UploadTileMesh(x, y, z):
    MAPBOX.GetImageTile(
        MapboxAPI.Tilesets.TERRAIN_DEM, x, y, z, ".pngraw", SAVED_HEIGHTMAP_PATH
    )
    GetHeightmappedMesh(x, y, z, SAVED_HEIGHTMAP_PATH, SAVED_MESH_PATH)
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


def GetHeightmappedMesh(x, y, z, heightmap_path, output_path):
    bpy.ops.wm.open_mainfile(filepath=BLENDER_TILE_PATH)
    tile = bpy.context.scene.objects[0]

    with Image.open(heightmap_path) as img:
        tile_size = 40075000 / pow(2, z)

        img = img.convert("RGB")
        width, height = img.size
        img_array = np.array(img, dtype=np.int32)

        # RGB to height conversion
        coeff = np.array([256 * 256, 256, 1], dtype=np.float32)
        height_map_2d = -10000 + (np.tensordot(img_array, coeff, axes=([2], [0])) * 0.1)
        height_map_2d = np.clip(height_map_2d / tile_size, a_min=0, a_max=None)

        mesh = tile.data

        # Resize height_map_2d to 32x32 to match mesh vertices
        resized_height_map = zoom(
            height_map_2d,
            (
                TILE_VERTEX_LENGTH / height_map_2d.shape[0],
                TILE_VERTEX_LENGTH / height_map_2d.shape[1],
            ),
        )

        # plt.imshow(height_map_2d, cmap="terrain")
        # plt.show()

        max_height = 0

        # Apply heights to mesh vertices
        for i, vertex in enumerate(mesh.vertices):
            if vertex.co.z == 0:
                continue

            x_idx = int(np.round(vertex.co.x * (TILE_VERTEX_LENGTH - 1)))
            y_idx = int(np.round((1 - vertex.co.y) * (TILE_VERTEX_LENGTH - 1)))

            height = resized_height_map[y_idx, x_idx]

            vertex.co.z = height
            max_height = max(max_height, height)

        SaveTileToJSON(x, y, z, max_height / 2, MESH_VERT_OFFSET_PATH)

    # bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
    # bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bpy.ops.export_scene.fbx(filepath=output_path)


if __name__ == "__main__":
    UploadTileMesh(544, 358, 10)
