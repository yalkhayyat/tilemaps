from src.libs.rbx_open_cloud import *
from src.libs.mapbox import *
import logging
from src.libs.quadtree import *
from src.config import *
from src.handlers.assets import AssetHandler, TileReprocessingError
from src.handlers.images import UploadTileImg
from src.handlers.meshes import UploadTileMesh, UploadFlatTileMesh
from src.database.sqlite import TableType, TableHasTile
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
    process_all_nodes: bool = False,
):
    if stats is None:
        stats = {"processed": 0, "skipped": 0}

    # Process if leaf node OR if we are forcing all nodes
    should_process = tile.is_leaf or process_all_nodes

    if should_process:
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
        recurseProcessTile(child, asset_handler, existing_db_path, asset_type, stats, process_all_nodes)

    return stats

def process_asset_type_flow(quadtree, handler, db_path, asset_label, process_all_nodes=False):
    """Run the processing flow for a specific asset type."""
    try:
        logging.info(f"Processing {asset_label} tiles...")
        stats = recurseProcessTile(quadtree.root, handler, db_path, asset_label, stats=None, process_all_nodes=process_all_nodes)
        logging.info(f"{asset_label.capitalize()} tiles - Processed: {stats['processed']}, Skipped: {stats['skipped']}")
        
        handler.RetrieveAllAssetIds()
        handler.ReProcessMissedTiles()
        
        return stats
    except TileReprocessingError as e:
        logging.error(e)
        return {"processed": 0, "skipped": 0}


def exportAssetsJson(db_path, output_json_path):
    """
    Export all asset IDs from the database to a JSON file.
    Format: {"x_y_z": {"mesh": "id", "img": "id"}}
    """
    if not db_path or not os.path.exists(db_path):
        logging.warning("No database found to export assets from.")
        return

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    assets = {}

    try:
        # Fetch Image IDs
        cursor.execute(f"SELECT x, y, z, value FROM {TableType.IMG_ASSET_IDS}")
        for row in cursor.fetchall():
            key = f"{row['x']}_{row['y']}_{row['z']}"
            if key not in assets:
                assets[key] = {}
            assets[key]["img"] = row['value']

        # Fetch Mesh IDs
        cursor.execute(f"SELECT x, y, z, value FROM {TableType.MESH_ASSET_IDS}")
        for row in cursor.fetchall():
            key = f"{row['x']}_{row['y']}_{row['z']}"
            if key not in assets:
                assets[key] = {}
            assets[key]["mesh"] = row['value']

        # Fetch Mesh Vert Offsets
        cursor.execute(f"SELECT x, y, z, value FROM {TableType.MESH_VERT_OFFSETS}")
        for row in cursor.fetchall():
            key = f"{row['x']}_{row['y']}_{row['z']}"
            if key not in assets:
                assets[key] = {}
            assets[key]["mesh_vert"] = row['value']
            
        # Write to JSON
        with open(output_json_path, "w") as f:
            json.dump(assets, f, indent=2, sort_keys=True)
            
        logging.info(f"Exported asset map to: {output_json_path}")
        logging.info(f"Total entries: {len(assets)}")

    except Exception as e:
        logging.error(f"Failed to export assets JSON: {str(e)}")
    finally:
        conn.close()


def recurseProcessTile(
    tile: Tile,
    asset_handler: AssetHandler,
    existing_db_path: str = None,
    asset_type: str = None,
    stats: dict = None,
    process_all_nodes: bool = False,
):
    if stats is None:
        stats = {"processed": 0, "skipped": 0}

    # Process if leaf node OR if we are forcing all nodes
    should_process = tile.is_leaf or process_all_nodes

    if should_process:
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
                # If we are strictly processing all nodes, we might re-process parent nodes here 
                # but valid checks prevent duplicate work usually.
                logging.debug(
                    f"Processing {asset_type} tile ({tile.x}, {tile.y}, {tile.zoom}) - not found in existing database"
                )

        asset_handler.UploadTile(tile.x, tile.y, tile.zoom)
        stats["processed"] += 1

    for child in tile.children:
        recurseProcessTile(child, asset_handler, existing_db_path, asset_type, stats, process_all_nodes)

    return stats

def process_asset_type_flow(quadtree, handler, db_path, asset_label, process_all_nodes=False):
    """Run the processing flow for a specific asset type."""
    try:
        logging.info(f"Processing {asset_label} tiles...")
        stats = recurseProcessTile(quadtree.root, handler, db_path, asset_label, stats=None, process_all_nodes=process_all_nodes)
        logging.info(f"{asset_label.capitalize()} tiles - Processed: {stats['processed']}, Skipped: {stats['skipped']}")
        
        handler.RetrieveAllAssetIds()
        handler.ReProcessMissedTiles()
        
        return stats
    except TileReprocessingError as e:
        logging.error(e)
        return {"processed": 0, "skipped": 0}


def main(args):
    quadtree = QuadTree(QUADTREE_ROOT, QUADTREE_MAX_LOD, QUADTREE_LOD_THRESHOLD, disable_lod=args.disable_lod)
    for airport in QUADTREE_AIRPORTS:
        quadtree.AddPoint(AIRPORTS[airport]["lat"], AIRPORTS[airport]["lon"])
    quadtree.BuildTree()

    # Check existing DB
    existing_db_path = args.existing_db if hasattr(args, "existing_db") and args.existing_db and os.path.exists(args.existing_db) else None
    if args.existing_db and not existing_db_path:
        logging.warning(f"Existing database not found: {args.existing_db}")
    elif existing_db_path:
        logging.info(f"Using existing database for tile checking: {existing_db_path}")

    # Initialize handlers
    img_handler = AssetHandler(
        UNIFIED_DB_PATH,
        TableType.IMG_ASSET_IDS,
        TableType.IMG_OPERATIONS,
        TableType.MISSED_IMG,
        UploadTileImg,
    )
    mesh_handler = AssetHandler(
        UNIFIED_DB_PATH,
        TableType.MESH_ASSET_IDS,
        TableType.MESH_OPERATIONS,
        TableType.MISSED_MESH,
        UploadTileMesh,
    )

    stats = {"img": {"processed": 0, "skipped": 0}, "mesh": {"processed": 0, "skipped": 0}}
    
    # Process assets based on arguments
    if args.asset in ["all", "img"]:
        stats["img"] = process_asset_type_flow(quadtree, img_handler, existing_db_path, "img", args.process_all_nodes)
        
    if args.asset in ["all", "mesh"]:
        stats["mesh"] = process_asset_type_flow(quadtree, mesh_handler, existing_db_path, "mesh", args.process_all_nodes)

    # Log overall statistics
    if args.asset == "all":
        total_processed = stats["img"]["processed"] + stats["mesh"]["processed"]
        total_skipped = stats["img"]["skipped"] + stats["mesh"]["skipped"]
        total_tiles = total_processed + total_skipped
        
        logging.info(f"Overall - Total tiles: {total_tiles}, Processed: {total_processed}, Skipped: {total_skipped}")
        
        if total_tiles > 0:
            skip_percentage = (total_skipped / total_tiles) * 100
            logging.info(f"Efficiency - {skip_percentage:.1f}% of tiles were skipped (already existed)")

    # Export JSON if requested
    if args.output_json:
        exportAssetsJson(UNIFIED_DB_PATH, args.output_json)

parser = argparse.ArgumentParser(
    description="Generate tiles for tilemaps with optional existing database checking",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  %(prog)s --asset all
  %(prog)s --asset img --existing-db previous_run/tiles.db
  %(prog)s --asset mesh --process-all-nodes --disable-lod
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

parser.add_argument(
    "--process-all-nodes",
    action="store_true",
    help="If set, process ALL nodes in the quadtree, not just leaf nodes."
)

parser.add_argument(
    "--disable-lod",
    action="store_true",
    help="If set, disable LOD logic and subdivide all tiles up to MAX_LOD."
)

parser.add_argument(
    "--output-json",
    type=str,
    help="Path to output a JSON dictionary of all asset IDs {x_y_z: {mesh: id, img: id}}"
)

if __name__ == "__main__":
    args = parser.parse_args()
    main(args)
