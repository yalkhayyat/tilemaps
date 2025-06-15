from rbx_open_cloud import *
from mapbox import *
import logging
from img_utils import *
from tile_quadtree import *
from config import *
from asset_handler import AssetHandler, TileReprocessingError
from img_handler import UploadTileImg
from mesh_handler import UploadTileMesh, UploadFlatTileMesh
from sqlite import TableType, TableHasTile
import argparse
import json
import os


def tileExistsInDatabase(x: int, y: int, z: int, db_path: str, asset_type: str) -> bool:
    """
    Check if a tile already exists in the database for the given asset type.

    Args:
        x, y, z: Tile coordinates
        db_path: Path to the database file
        asset_type: Either 'img' or 'mesh'

    Returns:
        True if tile exists and doesn't need processing, False otherwise
    """
    if not db_path or not os.path.exists(db_path):
        return False

    try:
        if asset_type == "img":
            # For image tiles, check if asset ID exists
            return TableHasTile(x, y, z, db_path, TableType.IMG_ASSET_IDS)

        elif asset_type == "mesh":
            # For mesh tiles, check if BOTH asset ID and vertex offset exist
            has_asset_id = TableHasTile(x, y, z, db_path, TableType.MESH_ASSET_IDS)
            has_vert_offset = TableHasTile(
                x, y, z, db_path, TableType.MESH_VERT_OFFSETS
            )
            return has_asset_id and has_vert_offset

        else:
            logging.warning(f"Unknown asset type: {asset_type}")
            return False

    except Exception as e:
        logging.warning(f"Error checking tile existence for ({x}, {y}, {z}): {str(e)}")
        return False


def recurseProcessTile(
    tile: Tile,
    asset_handler: AssetHandler,
    existing_db_path: str = None,
    asset_type: str = None,
    stats: dict = None,
):
    if stats is None:
        stats = {"processed": 0, "skipped": 0}

    if tile.is_leaf:
        # Check if tile already exists in the database
        if existing_db_path and asset_type:
            if tileExistsInDatabase(
                tile.x, tile.y, tile.zoom, existing_db_path, asset_type
            ):
                logging.debug(
                    f"Skipping {asset_type} tile ({tile.x}, {tile.y}, {tile.zoom}) - already exists in database"
                )
                stats["skipped"] += 1
                return stats
            else:
                logging.debug(
                    f"Processing {asset_type} tile ({tile.x}, {tile.y}, {tile.zoom}) - not found in existing database"
                )

        asset_handler.UploadTile(tile.x, tile.y, tile.zoom)
        stats["processed"] += 1

    for child in tile.children:
        recurseProcessTile(child, asset_handler, existing_db_path, asset_type, stats)

    return stats


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

    # Check if existing database is provided and exists
    existing_db_path = args.existing_db if hasattr(args, "existing_db") else None
    if existing_db_path:
        if os.path.exists(existing_db_path):
            logging.info(
                f"Using existing database for tile checking: {existing_db_path}"
            )
        else:
            logging.warning(f"Existing database not found: {existing_db_path}")
            existing_db_path = None

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
            logging.info("Processing image tiles...")
            img_stats = recurseProcessTile(quadtree.root, img, existing_db_path, "img")
            logging.info(
                f"Image tiles - Processed: {img_stats['processed']}, Skipped: {img_stats['skipped']}"
            )
            img.RetrieveAllAssetIds()
            img.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)

        try:
            logging.info("Processing mesh tiles...")
            mesh_stats = recurseProcessTile(
                quadtree.root, mesh, existing_db_path, "mesh"
            )
            logging.info(
                f"Mesh tiles - Processed: {mesh_stats['processed']}, Skipped: {mesh_stats['skipped']}"
            )
            mesh.RetrieveAllAssetIds()
            mesh.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)

        # Log overall statistics
        total_processed = img_stats["processed"] + mesh_stats["processed"]
        total_skipped = img_stats["skipped"] + mesh_stats["skipped"]
        total_tiles = total_processed + total_skipped
        logging.info(
            f"Overall - Total tiles: {total_tiles}, Processed: {total_processed}, Skipped: {total_skipped}"
        )
        if total_tiles > 0:
            skip_percentage = (total_skipped / total_tiles) * 100
            logging.info(
                f"Efficiency - {skip_percentage:.1f}% of tiles were skipped (already existed)"
            )

    elif args.asset == "img":
        try:
            logging.info("Processing image tiles only...")
            img_stats = recurseProcessTile(quadtree.root, img, existing_db_path, "img")
            logging.info(
                f"Image tiles - Processed: {img_stats['processed']}, Skipped: {img_stats['skipped']}"
            )
            img.RetrieveAllAssetIds()
            img.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)

    elif args.asset == "mesh":
        try:
            logging.info("Processing mesh tiles only...")
            mesh_stats = recurseProcessTile(
                quadtree.root, mesh, existing_db_path, "mesh"
            )
            logging.info(
                f"Mesh tiles - Processed: {mesh_stats['processed']}, Skipped: {mesh_stats['skipped']}"
            )
            mesh.RetrieveAllAssetIds()
            mesh.ReProcessMissedTiles()
        except TileReprocessingError as e:
            print(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate tiles for tilemaps with optional existing database checking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --asset all
  %(prog)s --asset img --existing-db previous_run/tiles.db
  %(prog)s --asset mesh --existing-db /path/to/existing/tiles.db
        """,
    )

    parser.add_argument(
        "-a",
        "--asset",
        type=str,
        choices=["all", "img", "mesh"],
        default="all",
        help="Asset type to process: all, img, or mesh (default: all)",
    )

    parser.add_argument(
        "--existing-db",
        type=str,
        help="Path to existing database to check for already processed tiles",
    )

    args = parser.parse_args()

    main(args)
