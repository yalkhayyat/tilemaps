import dotenv, os, logging, random
from logging_format import TerminalFormatter, FileFormatter
from rbx_open_cloud import OpenCloudClient
from mapbox import MapboxClient
import airportsdata
from datetime import datetime
from tile_quadtree import Tile

# Environment variables

dotenv.load_dotenv()
ROBLOX_API_KEY = os.getenv("ROBLOX_API_KEY")
ROBLOX_USER_ID = os.getenv("ROBLOX_USER_ID")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")

# Constants and Path setup

ID = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

SAVED_IMG_PATH = os.path.join("output", ID, "img.jpg")
SAVED_HEIGHTMAP_PATH = os.path.join("output", ID, "img.png")
SAVED_MESH_PATH = os.path.join("output", ID, "mesh.fbx")

IMG_ASSET_ID_PATH = os.path.join("output", ID, "img_asset_ids.json")
MESH_ASSET_ID_PATH = os.path.join("output", ID, "mesh_asset_ids.json")

IMG_OPERATIONS_PATH = os.path.join("output", ID, "img_operations.json")
MESH_OPERATIONS_PATH = os.path.join("output", ID, "mesh_operations.json")

MISSED_IMG_PATH = os.path.join("output", ID, "missed_img.json")
MISSED_MESH_PATH = os.path.join("output", ID, "missed_mesh.json")

LOGS_PATH = os.path.join("output", ID, "logs.txt")

BLENDER_PATH = "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"
BLENDER_TILE_PATH = os.path.join("assets", "mesh_tile.blend")

MESH_VERT_OFFSET_PATH = os.path.join("output", ID, "mesh_offsets.json")

TILE_VERTEX_LENGTH = 32

os.makedirs(f"output/{ID}")

ROBLOX = OpenCloudClient(ROBLOX_API_KEY, ROBLOX_USER_ID, 15)
MAPBOX = MapboxClient(MAPBOX_API_KEY, 15)
AIRPORTS = airportsdata.load()


# Logging setup

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
stream.setFormatter(TerminalFormatter())

fh = logging.FileHandler(LOGS_PATH)
fh.setLevel(logging.DEBUG)
fh.setFormatter(FileFormatter())

logger.addHandler(stream)
logger.addHandler(fh)

# Map Generation Settings

QUADTREE_ROOT = Tile(332, 459, 10)
QUADTREE_MAX_LOD = 10
QUADTREE_LOD_THRESHOLD = 10
QUADTREE_AIRPORTS = [
    "TNCM",
]
