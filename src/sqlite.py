import sqlite3
from enum import Enum


class TableType(Enum):
    """Enum for different table types in the unified database."""

    IMG_ASSET_IDS = "img_asset_ids"
    MESH_ASSET_IDS = "mesh_asset_ids"
    IMG_OPERATIONS = "img_operations"
    MESH_OPERATIONS = "mesh_operations"
    MISSED_IMG = "missed_img"
    MISSED_MESH = "missed_mesh"
    MESH_VERT_OFFSETS = "mesh_vert_offsets"


def _get_connection(db_path):
    """Get a database connection and ensure all tables exist."""
    conn = sqlite3.connect(db_path)

    # Create all tables if they don't exist
    cursor = conn.cursor()

    for table_type in TableType:
        table_name = table_type.value
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                x INTEGER,
                y INTEGER,
                z INTEGER,
                value TEXT,
                PRIMARY KEY (x, y, z)
            )
        """
        )

    conn.commit()
    return conn


def SaveTileToSQLite(x, y, z, value, db_path, table_type=None):
    """Save a tile value to the specified table in the database."""
    # For backward compatibility, if no table_type specified, use the old behavior
    if table_type is None:
        # This is for the old mesh_vert_offsets functionality
        table_name = "tiles"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tiles (
                x INTEGER,
                y INTEGER,
                z INTEGER,
                value TEXT,
                PRIMARY KEY (x, y, z)
            )
        """
        )
    else:
        conn = _get_connection(db_path)
        cursor = conn.cursor()
        table_name = table_type.value

    cursor.execute(
        f"""
        INSERT INTO {table_name} (x, y, z, value)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(x, y, z) DO UPDATE SET value = excluded.value
    """,
        (x, y, z, value),
    )

    conn.commit()
    conn.close()


def LoadTileValueFromSQLite(x, y, z, db_path, table_type=None):
    """Load a tile value from the specified table in the database."""
    # For backward compatibility, if no table_type specified, use the old behavior
    if table_type is None:
        # This is for the old mesh_vert_offsets functionality
        table_name = "tiles"
        conn = sqlite3.connect(db_path)
    else:
        conn = _get_connection(db_path)
        table_name = table_type.value

    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT value FROM {table_name}
        WHERE x = ? AND y = ? AND z = ?
    """,
        (x, y, z),
    )

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def GetAllTilesFromTable(db_path, table_type):
    """Get all tiles from a specific table."""
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT x, y, z, value FROM {table_type.value}
    """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def DeleteTileFromSQLite(x, y, z, db_path, table_type):
    """Delete a tile from the specified table in the database."""
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        DELETE FROM {table_type.value}
        WHERE x = ? AND y = ? AND z = ?
    """,
        (x, y, z),
    )

    conn.commit()
    conn.close()


def TableHasTile(x, y, z, db_path, table_type):
    """Check if a tile exists in the specified table."""
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        f"""
        SELECT 1 FROM {table_type.value}
        WHERE x = ? AND y = ? AND z = ?
        LIMIT 1
    """,
        (x, y, z),
    )

    exists = cursor.fetchone() is not None
    conn.close()

    return exists


def GetTableTileCount(db_path, table_type):
    """Get the count of tiles in a specific table."""
    conn = _get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) FROM {table_type.value}")

    count = cursor.fetchone()[0]
    conn.close()

    return count
