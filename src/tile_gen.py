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


def recurseProcessTile(tile: Tile, asset_handler: AssetHandler):
    if tile.is_leaf:
        asset_handler.UploadTile(tile.x, tile.y, tile.zoom)

    for child in tile.children:
        recurseProcessTile(child, asset_handler)


def main(args):
    quadtree = QuadTree(QUADTREE_ROOT, QUADTREE_MAX_LOD, QUADTREE_LOD_THRESHOLD)
    for airport in QUADTREE_AIRPORTS:
        quadtree.AddPoint(AIRPORTS[airport]["lat"], AIRPORTS[airport]["lon"])
    quadtree.BuildTree()

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
