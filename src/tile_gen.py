from rbx_open_cloud import *
from mapbox import *
import logging
from img_utils import *
from tile_quadtree import *
from config import *
from asset_handler import AssetHandler, TileReprocessingError
from img_handler import UploadTileImg
from mesh_handler import UploadTileMesh, UploadFlatTileMesh
from sqlite import TableType
import argparse
import json
import os


def recurseProcessTile(tile: Tile, asset_handler: AssetHandler):
    if tile.is_leaf:
        asset_handler.UploadTile(tile.x, tile.y, tile.zoom)

    for child in tile.children:
        recurseProcessTile(child, asset_handler)


def collectLeafTiles(tile: Tile, leaf_tiles: list):
    """Recursively collect all leaf tiles from the quadtree."""
    if tile.is_leaf:
        leaf_tiles.append(tile)

    for child in tile.children:
        collectLeafTiles(child, leaf_tiles)


def createTileManifest(quadtree_root: Tile) -> dict:
    """
    Create a tile manifest JSON file listing all leaf tiles.

    Args:
        quadtree_root: The root tile of the quadtree

    Returns:
        Dictionary containing the tile manifest
    """
    # Collect all leaf tiles
    leaf_tiles = []
    collectLeafTiles(quadtree_root, leaf_tiles)

    # Create manifest dictionary with tile keys and 'true' values
    manifest = {}
    for tile in leaf_tiles:
        # Use the same key format as the datastore (tile_x_y_z)
        tile_key = f"tile_{tile.x}_{tile.y}_{tile.zoom}"
        manifest[tile_key] = True

    output_path = os.path.join("output", ID, "tile_manifest.json")

    # Write manifest to JSON file
    try:
        with open(output_path, "w") as f:
            json.dump(manifest, f, indent=2, sort_keys=True)

        logging.info(f"Tile manifest created: {output_path}")
        logging.info(f"Total leaf tiles: {len(leaf_tiles)}")

    except Exception as e:
        logging.error(f"Failed to create tile manifest: {str(e)}")
        raise

    return manifest


def main(args):
    quadtree = QuadTree(QUADTREE_ROOT, QUADTREE_MAX_LOD, QUADTREE_LOD_THRESHOLD)
    for airport in QUADTREE_AIRPORTS:
        quadtree.AddPoint(AIRPORTS[airport]["lat"], AIRPORTS[airport]["lon"])
    quadtree.BuildTree()

    # Create tile manifest after building the quadtree
    try:
        manifest = createTileManifest(quadtree.root)
        logging.info("Tile manifest generation completed successfully")
    except Exception as e:
        logging.error(f"Failed to create tile manifest: {str(e)}")

    img = AssetHandler(
        UNIFIED_DB_PATH,
        TableType.IMG_ASSET_IDS,
        TableType.IMG_OPERATIONS,
        TableType.MISSED_IMG,
        UploadTileImg,
    )
    mesh = AssetHandler(
        UNIFIED_DB_PATH,
        TableType.MESH_ASSET_IDS,
        TableType.MESH_OPERATIONS,
        TableType.MISSED_MESH,
        UploadTileMesh,
    )

    if args.asset == "all":
        try:
            recurseProcessTile(quadtree.root, img)
            img.RetrieveAllAssetIds()
            img.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)

        try:
            recurseProcessTile(quadtree.root, mesh)
            mesh.RetrieveAllAssetIds()
            mesh.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--asset", type=str, default="all")
    args = parser.parse_args()

    main(args)
