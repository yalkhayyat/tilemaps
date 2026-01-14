from src.config import *
from src.libs.rbx_open_cloud import AssetType, ContentType
from src.libs.mapbox import *
import argparse, subprocess
import bpy
from PIL import Image
import numpy as np
from scipy.ndimage import map_coordinates
import math
import mercantile
from src.database.sqlite import SaveTileToSQLite, TableType

bpy.app.binary_path = BLENDER_PATH
logging.info(f"Using Blender version: {bpy.app.version_string}")

def UploadTileMesh(x, y, z):
    TERRAIN_CLIENT.GetImageTile(
        TERRAIN_TILE_CONFIG["tileset_id"],
        x, y, z,
        TERRAIN_TILE_CONFIG["file_format"],
        SAVED_HEIGHTMAP_PATH,
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
    TERRAIN_CLIENT.GetImageTile(
        TERRAIN_TILE_CONFIG["tileset_id"],
        x, y, z,
        TERRAIN_TILE_CONFIG["file_format"],
        SAVED_HEIGHTMAP_PATH,
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


def mercator_to_sphere_numpy(lat_deg, lon_deg, radius):
    lat_rad = np.radians(lat_deg)
    lon_rad = np.radians(lon_deg)
    X = radius * np.cos(lat_rad) * np.cos(lon_rad)
    Y = radius * np.cos(lat_rad) * np.sin(lon_rad)
    Z = radius * np.sin(lat_rad)
    return X, Y, Z

def GetHeightmappedMesh(x, y, z, heightmap_path, output_path, spherical):
    bpy.ops.wm.open_mainfile(filepath=BLENDER_TILE_PATH)
    tile = bpy.context.scene.objects[0]
    mesh = tile.data

    with Image.open(heightmap_path) as img:
        img = img.convert("RGB")
        img_array = np.array(img, dtype=np.int32)

        # RGB to height conversion
        coeff = np.array(TERRAIN_ENCODING["coefficients"], dtype=np.float32)
        height_map_2d = TERRAIN_ENCODING["offset"] + (
            np.tensordot(img_array, coeff, axes=([2], [0])) * TERRAIN_ENCODING["multiplier"]
        )
        height_map_2d = np.clip(height_map_2d, a_min=0, a_max=None)

        
        # 1. Get all vertex coordinates into a NumPy array efficiently
        num_verts = len(mesh.vertices)
        coords_flat = np.zeros(num_verts * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", coords_flat)
        verts = coords_flat.reshape(num_verts, 3)

        # 2. Sample heights using map_coordinates (No resizing needed!)
        src_h, src_w = height_map_2d.shape
        
        # Calculate sample coordinates based on UVs (verts X/Y are 0..1)
        # Y is inverted (1 - y)
        sample_rows = (1 - verts[:, 1]) * (src_h - 1)
        sample_cols = verts[:, 0] * (src_w - 1)
        query_coords = np.stack([sample_rows, sample_cols])

        # Get heights for all vertices at once using bilinear interpolation
        sampled_heights = map_coordinates(height_map_2d, query_coords, order=1, mode='nearest')

        # 3. Create a mask for vertices that should receive height (Z > 0)
        valid_mask = verts[:, 2] > 0

        if spherical:
            n = 1 << z
            
            # Vectorized Longitude Calculation
            lon_deg = (x + verts[:, 0]) / n * 360.0 - 180.0
            
            # Vectorized Latitude Calculation
            lat_arg = np.pi * (1 - 2 * (y + 1 - verts[:, 1]) / n)
            lat_rad = np.arctan(np.sinh(lat_arg))
            lat_deg = np.degrees(lat_rad)
            
            # Calculate Radius
            r = np.full(num_verts, 6378137.0)
            # Only add height to valid vertices
            r[valid_mask] += sampled_heights[valid_mask]
            
            # Convert to Spherical (Vectorized)
            x_s, y_s, z_s = mercator_to_sphere_numpy(
                lat_deg, 
                lon_deg, 
                r * 0.0001 * 0.01 # scale + fbx units
            )
            
            # Update vertex positions
            verts[:, 0] = x_s
            verts[:, 1] = y_s
            verts[:, 2] = z_s
            
        else:
            # Flat mode: Apply height scaling only to valid vertices
            scale_factor = 40075000 / (2**z)
            verts[valid_mask, 2] = sampled_heights[valid_mask] / scale_factor

        # 4. Write modified coordinates back to Blender
        mesh.vertices.foreach_set("co", verts.ravel())
        mesh.update()
        
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    SaveTileToSQLite(
        x,
        y,
        z,
        f"{tile.location.x}_{tile.location.y}_{tile.location.z}",
        UNIFIED_DB_PATH,
        TableType.MESH_VERT_OFFSETS,
    )

    bpy.ops.export_scene.fbx(filepath=output_path)