import logging
from config import *
from sqlite import (
    SaveTileToSQLite,
    LoadTileValueFromSQLite,
    GetAllTilesFromTable,
    DeleteTileFromSQLite,
    TableHasTile,
    TableType,
)


class TileReprocessingError(Exception):
    """Custom exception for tile reprocessing failures."""

    def __init__(self, message):
        super().__init__(message)


class AssetHandler:
    def __init__(
        self, db_path, asset_table_type, op_table_type, missed_table_type, upload_func
    ) -> None:
        self.db_path = db_path
        self.asset_table_type = asset_table_type
        self.op_table_type = op_table_type
        self.missed_table_type = missed_table_type
        self.upload_func = upload_func

    def UploadTile(self, x, y, z):
        try:
            op_id = self.upload_func(x, y, z)
            SaveTileToSQLite(x, y, z, op_id, self.db_path, self.op_table_type)
            logging.info(f"Sucessfully uploaded Tile: {x}_{y}_{z}.")
            return op_id
        except Exception as e:
            error = str(e)
            SaveTileToSQLite(x, y, z, error, self.db_path, self.missed_table_type)
            logging.error(f"Failed to upload Tile: {x}_{y}_{z}. Error: {error}")

    def RetrieveAssetIdTile(self, x, y, z, op_id):
        try:
            asset_id = ROBLOX.GetOperation(op_id)
            SaveTileToSQLite(
                x, y, z, f"rbxassetid://{asset_id}", self.db_path, self.asset_table_type
            )
            logging.info(f"Sucessfully retrieved Asset ID for Tile: {x}_{y}_{z}.")
        except Exception as e:
            error = str(e)
            SaveTileToSQLite(x, y, z, error, self.db_path, self.missed_table_type)
            logging.error(
                f"Failed to retrieve Asset ID for Tile: {x}_{y}_{z}. Error: {error}"
            )

            # pass the exception upwards
            raise e

    def RetrieveAllAssetIds(self):
        # Get all operation IDs from the operations table
        tile_ops = GetAllTilesFromTable(self.db_path, self.op_table_type)

        for x, y, z, op_id in tile_ops:
            # Check if asset ID already exists for this tile
            if TableHasTile(x, y, z, self.db_path, self.asset_table_type):
                continue

            try:
                self.RetrieveAssetIdTile(x, y, z, op_id)
            except:
                ...
                # no need to do anything
                # feels wrong, refactor later

    def ReProcessMissedTiles(self):
        max_retries = 5

        # Get all missed tiles
        missed_tiles = GetAllTilesFromTable(self.db_path, self.missed_table_type)

        if not missed_tiles:
            return

        for attempt in range(1, max_retries + 1):
            logging.info(f"Reprocessing attempt {attempt}/{max_retries}...")

            reprocessed_tiles = []

            for x, y, z, error_msg in missed_tiles:
                try:
                    # Start from the upload step
                    op_id = self.UploadTile(x, y, z)
                    self.RetrieveAssetIdTile(x, y, z, op_id)
                    logging.info(f"Successfully reprocessed Tile: {x}_{y}_{z}.")
                    reprocessed_tiles.append((x, y, z))
                except Exception as e:
                    logging.warning(
                        f"Attempt {attempt} failed for Tile: {x}_{y}_{z}. Error: {e}"
                    )

            # Remove successfully reprocessed tiles from missed_tiles table
            for x, y, z in reprocessed_tiles:
                DeleteTileFromSQLite(x, y, z, self.db_path, self.missed_table_type)

            # Refresh missed tiles list for next iteration
            missed_tiles = GetAllTilesFromTable(self.db_path, self.missed_table_type)

            if not missed_tiles:
                logging.info("All missed tiles successfully reprocessed.")
                return

        # If still tiles are missing after max_retries, raise the custom exception
        if missed_tiles:
            failed_tiles = [f"{x}_{y}_{z}" for x, y, z, _ in missed_tiles]
            error_message = f"Failed to reprocess the following tiles after {max_retries} attempts: {failed_tiles}"
            logging.error(error_message)
            raise TileReprocessingError(error_message)
