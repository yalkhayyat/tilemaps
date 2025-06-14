"""
Script to upload SQLite database contents to Roblox Datastore using Open Cloud API.
Each table will be uploaded to its own separate datastore.

Usage:
    python sqlite_to_datastore.py <path_to_db_file> [options]

Example:
    python sqlite_to_datastore.py output/2024-01-01_12-00-00/tiles.db --universe-id 123456789
    python sqlite_to_datastore.py tiles.db --universe-id 123456789 --datastore-prefix MyProject_
"""

import argparse
import sqlite3
import json
import logging
import os
import sys
from typing import Dict, List, Tuple, Optional
import dotenv
from rbx_open_cloud import OpenCloudClient
from sqlite import TableType, GetAllTilesFromTable


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("sqlite_to_datastore.log"),
        ],
    )


def load_environment():
    """Load environment variables."""
    dotenv.load_dotenv()

    api_key = os.getenv("ROBLOX_API_KEY")
    user_id = os.getenv("ROBLOX_USER_ID")

    if not api_key or not user_id:
        raise ValueError(
            "ROBLOX_API_KEY and ROBLOX_USER_ID must be set in environment variables"
        )

    return api_key, user_id


def get_table_info(db_path: str) -> Dict[str, int]:
    """Get information about all tables in the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    table_info = {}
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        table_info[table_name] = count

    conn.close()
    return table_info


def create_tile_key(x: int, y: int, z: int) -> str:
    """Create a standardized key for tile coordinates."""
    return f"tile_{x}_{y}_{z}"


def create_datastore_name(table_name: str, prefix: str = "", suffix: str = "") -> str:
    """Create a datastore name for a table with optional prefix and suffix."""
    # Convert table name to a clean format (remove underscores, capitalize)
    clean_name = table_name.replace("_", "").title()
    return f"{prefix}{clean_name}{suffix}"


def batch_upload_tiles(
    client: OpenCloudClient,
    datastore_name: str,
    table_name: str,
    tiles: List[Tuple[int, int, int, str]],
    batch_size: int = 100,
) -> None:
    """Upload tiles to datastore in batches with error handling."""
    total_tiles = len(tiles)
    successful_uploads = 0
    failed_uploads = 0

    logging.info(
        f"Starting upload of {total_tiles} tiles from table '{table_name}' to datastore '{datastore_name}'"
    )

    for i in range(0, total_tiles, batch_size):
        batch = tiles[i : i + batch_size]
        batch_start = i + 1
        batch_end = min(i + batch_size, total_tiles)

        logging.info(f"Processing batch {batch_start}-{batch_end} of {total_tiles}")

        for x, y, z, value in batch:
            try:
                # Create a unique key for this tile
                entry_key = create_tile_key(x, y, z)

                # Prepare the data to store
                tile_data = {
                    "x": x,
                    "y": y,
                    "z": z,
                    "value": value,
                    "table": table_name,
                    "uploaded_at": str(int(time.time())),
                }

                # Upload to datastore
                result = client.SetDatastoreEntry(
                    datastore_name=datastore_name,
                    entry_key=entry_key,
                    data=tile_data,
                    scope="global",
                )

                successful_uploads += 1
                logging.debug(
                    f"Successfully uploaded tile ({x}, {y}, {z}) from {table_name}"
                )

            except Exception as e:
                failed_uploads += 1
                logging.error(
                    f"Failed to upload tile ({x}, {y}, {z}) from {table_name}: {str(e)}"
                )

        # Small delay between batches to avoid rate limiting
        if i + batch_size < total_tiles:
            logging.info(
                f"Completed batch {batch_start}-{batch_end}. Waiting 1 second before next batch..."
            )
            time.sleep(1)

    logging.info(
        f"Upload complete for table '{table_name}': {successful_uploads} successful, {failed_uploads} failed"
    )


def upload_table_to_datastore(
    client: OpenCloudClient,
    db_path: str,
    table_type: TableType,
    datastore_name: str,
    batch_size: int,
) -> None:
    """Upload a specific table's contents to datastore."""
    try:
        # Get all tiles from the table
        tiles = GetAllTilesFromTable(db_path, table_type)

        if not tiles:
            logging.warning(f"No tiles found in table '{table_type.value}'")
            return

        # Upload tiles in batches
        batch_upload_tiles(client, datastore_name, table_type.value, tiles, batch_size)

    except Exception as e:
        logging.error(f"Error uploading table '{table_type.value}': {str(e)}")
        raise


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Upload SQLite database contents to Roblox Datastore",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s tiles.db --universe-id 123456789
  %(prog)s tiles.db --universe-id 123456789 --datastore-prefix MyProject_ --tables IMG_ASSET_IDS MESH_ASSET_IDS
  %(prog)s tiles.db --universe-id 123456789 --datastore-prefix Game_ --datastore-suffix _Data --batch-size 50 --dry-run
        """,
    )

    parser.add_argument("db_path", help="Path to the SQLite database file")

    parser.add_argument(
        "--universe-id", required=True, help="Roblox Universe ID for the datastore"
    )

    parser.add_argument(
        "--datastore-prefix",
        default="",
        help="Prefix for datastore names (default: no prefix)",
    )

    parser.add_argument(
        "--datastore-suffix",
        default="",
        help="Suffix for datastore names (default: no suffix)",
    )

    parser.add_argument(
        "--tables",
        nargs="*",
        choices=[t.name for t in TableType],
        help="Specific tables to upload (default: all tables)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of tiles to upload per batch (default: 100)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=15,
        help="Maximum number of retries for API requests (default: 15)",
    )

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate database file
    if not os.path.exists(args.db_path):
        logging.error(f"Database file not found: {args.db_path}")
        sys.exit(1)

    # Load environment variables
    try:
        api_key, user_id = load_environment()
    except ValueError as e:
        logging.error(str(e))
        sys.exit(1)

    # Get database information
    try:
        table_info = get_table_info(args.db_path)
        logging.info(f"Database contains {len(table_info)} tables:")
        for table_name, count in table_info.items():
            logging.info(f"  - {table_name}: {count} entries")
    except Exception as e:
        logging.error(f"Error reading database: {str(e)}")
        sys.exit(1)

    # Determine which tables to upload
    if args.tables:
        tables_to_upload = [TableType[table_name] for table_name in args.tables]
    else:
        tables_to_upload = list(TableType)

    # Filter out tables that don't exist or are empty
    valid_tables = []
    for table_type in tables_to_upload:
        if table_type.value in table_info and table_info[table_type.value] > 0:
            valid_tables.append(table_type)
        else:
            logging.warning(f"Skipping table '{table_type.value}' (not found or empty)")

    if not valid_tables:
        logging.error("No valid tables found to upload")
        sys.exit(1)

    # Calculate total tiles to upload and show datastore mapping
    total_tiles = sum(table_info[table_type.value] for table_type in valid_tables)

    logging.info(
        f"Will upload {total_tiles} tiles from {len(valid_tables)} tables to individual datastores:"
    )
    for table_type in valid_tables:
        datastore_name = create_datastore_name(
            table_type.value, args.datastore_prefix, args.datastore_suffix
        )
        count = table_info[table_type.value]
        logging.info(
            f"  - Table '{table_type.value}' -> Datastore '{datastore_name}' ({count} tiles)"
        )

    if args.dry_run:
        logging.info("DRY RUN - No actual uploads will be performed")
        sys.exit(0)

    # Create Open Cloud client
    try:
        client = OpenCloudClient(
            api_key=api_key,
            user_id=user_id,
            max_retries=args.max_retries,
            universe_id=args.universe_id,
        )
        logging.info("Open Cloud client initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Open Cloud client: {str(e)}")
        sys.exit(1)

    # Upload each table to its own datastore
    overall_success = True
    for table_type in valid_tables:
        try:
            # Generate datastore name for this table
            datastore_name = create_datastore_name(
                table_type.value, args.datastore_prefix, args.datastore_suffix
            )

            logging.info(
                f"Starting upload for table '{table_type.value}' to datastore '{datastore_name}'"
            )
            upload_table_to_datastore(
                client, args.db_path, table_type, datastore_name, args.batch_size
            )
            logging.info(
                f"Completed upload for table '{table_type.value}' to datastore '{datastore_name}'"
            )
        except Exception as e:
            logging.error(f"Failed to upload table '{table_type.value}': {str(e)}")
            overall_success = False

    if overall_success:
        logging.info("All uploads completed successfully!")
    else:
        logging.error("Some uploads failed. Check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    import time

    main()
