from rbx_open_cloud import *
from mapbox import *
import json
import logging
from img_utils import *
from tile_quadtree import *
from config import *
from asset_handler import AssetHandler
from img_handler import UploadTileImg
from mesh_handler import UploadTileMesh
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
        IMG_ASSET_ID_PATH, IMG_OPERATIONS_PATH, MISSED_IMG_PATH, UploadTileImg
    )
    mesh = AssetHandler(
        MESH_ASSET_ID_PATH, MESH_OPERATIONS_PATH, MISSED_MESH_PATH, UploadTileMesh
    )

    if args.asset == "all":
        recurseProcessTile(quadtree.root, img)
        img.RetrieveAllAssetIds()
        img.ReProcessMissedTiles()

        recurseProcessTile(quadtree.root, mesh)
        mesh.RetrieveAllAssetIds()
        mesh.ReProcessMissedTiles()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--asset", type=str, default="all")
    args = parser.parse_args()

    main(args)
