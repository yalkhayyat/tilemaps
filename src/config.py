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

# Unified database path
UNIFIED_DB_PATH = os.path.join("output", ID, "tiles.db")

# Legacy paths for backward compatibility (now using single database)
IMG_ASSET_ID_PATH = UNIFIED_DB_PATH
MESH_ASSET_ID_PATH = UNIFIED_DB_PATH
IMG_OPERATIONS_PATH = UNIFIED_DB_PATH
MESH_OPERATIONS_PATH = UNIFIED_DB_PATH
MISSED_IMG_PATH = UNIFIED_DB_PATH
MISSED_MESH_PATH = UNIFIED_DB_PATH
MESH_VERT_OFFSET_PATH = UNIFIED_DB_PATH

LOGS_PATH = os.path.join("output", ID, "logs.txt")

BLENDER_PATH = "blender"
BLENDER_TILE_PATH = os.path.join("assets", "mesh_tile.blend")

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

QUADTREE_ROOT = Tile(0, 0, 0)
QUADTREE_MAX_LOD = 2
QUADTREE_LOD_THRESHOLD = 11
QUADTREE_AIRPORTS = [
    "KATL",  # Atlanta
    "KLAX",  # Los Angeles
    "KORD",  # Chicago
    "KDFW",  # Dallas Fort Worth
    "KDEN",  # Denver
    "KJFK",  # John F. Kennedy (New York City)
    "KSFO",  # San Francisco
    "KSEA",  # Seattle-Tacoma
    "KLAS",  # Harry Reid (Las Vegas)
    "KMIA",  # Miami
]
