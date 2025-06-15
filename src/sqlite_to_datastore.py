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


def create_chunk_key(chunk_id: int) -> str:
    """Create a standardized key for tile chunks."""
    return f"chunk_{chunk_id}"


def create_datastore_name(table_name: str, prefix: str = "", suffix: str = "") -> str:
    """Create a datastore name for a table with optional prefix and suffix."""
    # Convert table name to a clean format (remove underscores, capitalize)
    clean_name = table_name.replace("_", "").title()
    return f"{prefix}{clean_name}{suffix}"


def calculate_json_size(data: dict) -> int:
    """Calculate the size of data when encoded as JSON."""
    return len(json.dumps(data, separators=(",", ":")))


def create_tile_chunks(
    tiles: List[Tuple[int, int, int, str]],
    table_name: str,
    max_chunk_size: int = 4_000_000,
) -> List[dict]:
    """
    Group tiles into chunks that fit within datastore size limits.
    Tiles are formatted as "x_y_z": "assetid..." key-value pairs.

    Args:
        tiles: List of (x, y, z, value) tuples
        table_name: Name of the source table
        max_chunk_size: Maximum size in characters for each chunk (default: 4MB - buffer)

    Returns:
        List of chunk dictionaries ready for upload
    """
    chunks = []
    current_chunk_tiles = {}
    current_chunk_size = 0
    chunk_id = 0

    # Base chunk structure overhead
    base_chunk = {
        "tiles": {},
        "chunk_info": {
            "chunk_id": 0,
            "tile_count": 0,
            "table": table_name,
            "uploaded_at": str(int(time.time())),
        },
    }
    base_size = calculate_json_size(base_chunk)

    logging.info(f"Base chunk overhead: {base_size} characters")

    for x, y, z, value in tiles:
        # Create tile key in "x_y_z" format
        tile_key = f"{x}_{y}_{z}"

        # Calculate size of this key-value pair
        # Format: "key":"value",
        tile_entry_size = (
            len(json.dumps({tile_key: value}, separators=(",", ":"))) - 2
        )  # subtract {} brackets

        # Check if adding this tile would exceed the limit
        projected_size = current_chunk_size + tile_entry_size + base_size
        if current_chunk_tiles and projected_size > max_chunk_size:
            # Finalize current chunk
            chunk_data = {
                "tiles": current_chunk_tiles,
                "chunk_info": {
                    "chunk_id": chunk_id,
                    "tile_count": len(current_chunk_tiles),
                    "table": table_name,
                    "uploaded_at": str(int(time.time())),
                },
            }
            chunks.append(chunk_data)

            logging.debug(
                f"Created chunk {chunk_id} with {len(current_chunk_tiles)} tiles ({current_chunk_size + base_size} characters)"
            )

            # Start new chunk
            chunk_id += 1
            current_chunk_tiles = {}
            current_chunk_size = 0

        # Add tile to current chunk as key-value pair
        current_chunk_tiles[tile_key] = value
        current_chunk_size += tile_entry_size

    # Don't forget the last chunk
    if current_chunk_tiles:
        chunk_data = {
            "tiles": current_chunk_tiles,
            "chunk_info": {
                "chunk_id": chunk_id,
                "tile_count": len(current_chunk_tiles),
                "table": table_name,
                "uploaded_at": str(int(time.time())),
            },
        }
        chunks.append(chunk_data)

        logging.debug(
            f"Created final chunk {chunk_id} with {len(current_chunk_tiles)} tiles ({current_chunk_size + base_size} characters)"
        )

    return chunks


def batch_upload_chunks(
    client: OpenCloudClient,
    datastore_name: str,
    table_name: str,
    chunks: List[dict],
    delay_between_chunks: float = 1.0,
) -> None:
    """Upload tile chunks to datastore with error handling."""
    total_chunks = len(chunks)
    total_tiles = sum(chunk["chunk_info"]["tile_count"] for chunk in chunks)
    successful_chunks = 0
    failed_chunks = 0
    successful_tiles = 0

    logging.info(
        f"Starting upload of {total_tiles} tiles in {total_chunks} chunks from table '{table_name}' to datastore '{datastore_name}'"
    )

    for i, chunk_data in enumerate(chunks):
        chunk_id = chunk_data["chunk_info"]["chunk_id"]
        tile_count = chunk_data["chunk_info"]["tile_count"]

        try:
            # Create chunk key
            entry_key = create_chunk_key(chunk_id)

            # Validate key length (must be under 50 characters)
            if len(entry_key) >= 50:
                raise ValueError(f"Chunk key '{entry_key}' exceeds 50 character limit")

            # Validate data size
            chunk_size = calculate_json_size(chunk_data)
            if chunk_size >= 4_194_304:
                raise ValueError(
                    f"Chunk {chunk_id} data size ({chunk_size}) exceeds 4MB limit"
                )

            # Upload chunk to datastore
            result = client.SetDatastoreEntry(
                datastore_name=datastore_name,
                entry_key=entry_key,
                data=chunk_data,
                scope="global",
            )

            successful_chunks += 1
            successful_tiles += tile_count

            logging.info(
                f"Successfully uploaded chunk {chunk_id} with {tile_count} tiles ({chunk_size:,} characters) [{i+1}/{total_chunks}]"
            )

        except Exception as e:
            failed_chunks += 1
            logging.error(
                f"Failed to upload chunk {chunk_id} with {tile_count} tiles: {str(e)}"
            )

        # Delay between chunks to avoid rate limiting
        if i + 1 < total_chunks:
            logging.debug(
                f"Waiting {delay_between_chunks} seconds before next chunk..."
            )
            time.sleep(delay_between_chunks)

    logging.info(
        f"Upload complete for table '{table_name}': {successful_chunks}/{total_chunks} chunks successful, {successful_tiles}/{total_tiles} tiles uploaded"
    )


def upload_table_to_datastore(
    client: OpenCloudClient,
    db_path: str,
    table_type: TableType,
    datastore_name: str,
    max_chunk_size: int,
    delay_between_chunks: float = 1.0,
) -> None:
    """Upload a specific table's contents to datastore as optimized chunks."""
    try:
        # Get all tiles from the table
        tiles = GetAllTilesFromTable(db_path, table_type)

        if not tiles:
            logging.warning(f"No tiles found in table '{table_type.value}'")
            return

        logging.info(
            f"Creating optimized chunks for {len(tiles)} tiles from table '{table_type.value}'"
        )

        # Create tile chunks that fit within datastore limits
        chunks = create_tile_chunks(tiles, table_type.value, max_chunk_size)

        if not chunks:
            logging.warning(f"No chunks created for table '{table_type.value}'")
            return

        logging.info(f"Created {len(chunks)} chunks for table '{table_type.value}'")

        # Upload chunks to datastore
        batch_upload_chunks(
            client, datastore_name, table_type.value, chunks, delay_between_chunks
        )

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
  %(prog)s tiles.db --universe-id 123456789 --datastore-prefix Game_ --datastore-suffix _Data --max-chunk-size 3000000 --dry-run
  %(prog)s tiles.db --universe-id 123456789 --chunk-delay 0.5 --max-chunk-size 2000000
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
        "--max-chunk-size",
        type=int,
        default=4_000_000,
        help="Maximum size in characters for each chunk (default: 4MB with buffer)",
    )

    parser.add_argument(
        "--chunk-delay",
        type=float,
        default=1.0,
        help="Delay in seconds between chunk uploads (default: 1.0)",
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
                client,
                args.db_path,
                table_type,
                datastore_name,
                args.max_chunk_size,
                args.chunk_delay,
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
