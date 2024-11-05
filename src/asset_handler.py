import json, logging
from config import *


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


class AssetHandler:
    def __init__(
        self, asset_id_path, op_id_path, missed_tiles_path, upload_func
    ) -> None:
        self.asset_id_path = asset_id_path
        self.op_id_path = op_id_path
        self.missed_tiles_path = missed_tiles_path
        self.upload_func = upload_func

    def UploadTile(self, x, y, z):
        try:
            op_id = self.upload_func(x, y, z)
            SaveTileToJSON(x, y, z, op_id, self.op_id_path)
            logging.info(f"Sucessfully uploaded Tile: {x}_{y}_{z}.")
        except Exception as e:
            error = str(e)
            SaveTileToJSON(x, y, z, error, self.missed_tiles_path)
            logging.error(f"Failed to upload Tile: {x}_{y}_{z}. Error: {error}")

    def RetrieveAssetIdTile(self, x, y, z, op_id):
        try:
            asset_id = ROBLOX.GetOperation(op_id)
            SaveTileToJSON(x, y, z, f"rbxassetid://{asset_id}", self.asset_id_path)
            logging.info(f"Sucessfully retrieved Asset ID for Tile: {x}_{y}_{z}.")
        except Exception as e:
            error = str(e)
            SaveTileToJSON(x, y, z, error, self.missed_tiles_path)
            logging.error(
                f"Failed to retrieve Asset ID for Tile: {x}_{y}_{z}. Error: {error}"
            )

    def RetrieveAllAssetIds(self):
        try:
            with open(self.op_id_path, "r") as f:
                tile_ops = json.load(f)
        except FileNotFoundError:
            tile_ops = {}
        except json.JSONDecodeError:
            tile_ops = {}

        try:
            with open(self.asset_id_path, "r") as f:
                asset_ids = json.load(f)
        except FileNotFoundError:
            asset_ids = {}
        except json.JSONDecodeError:
            asset_ids = {}

        for tile, op_id in tile_ops.items():
            if tile in asset_ids.keys():
                continue

            tile_parts = tile.split("_")
            x = tile_parts[0]
            y = tile_parts[1]
            z = tile_parts[2]

            self.RetrieveAssetIdTile(x, y, z, op_id)

    def ReProcessMissedTiles(self):
        try:
            with open(self.missed_tiles_path, "r") as f:
                missed_tiles = json.load(f)
        except FileNotFoundError:
            missed_tiles = {}
        except json.JSONDecodeError:
            missed_tiles = {}

        for tile in missed_tiles.keys():
            tile_parts = tile.split("_")
            x = tile_parts[0]
            y = tile_parts[1]
            z = tile_parts[2]

            self.UploadTile(x, y, z)

        self.RetrieveAllAssetIds()
