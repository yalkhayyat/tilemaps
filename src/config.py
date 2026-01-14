import dotenv, os, logging, random
from src.utils.logger import TerminalFormatter, FileFormatter
from logging.handlers import RotatingFileHandler 
from src.libs.rbx_open_cloud import OpenCloudClient
from src.libs.mapbox import MapboxClient
from src.libs.eox import EOXClient
from src.libs.aws_terrain import AWSTerrainClient
import airportsdata
from datetime import datetime
from src.libs.quadtree import Tile

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

LOGS_PATH = os.path.join("output", ID, "logs.txt")

BLENDER_PATH = "blender"
BLENDER_TILE_PATH = os.path.join("assets", "mesh_tile.blend")

TILE_VERTEX_LENGTH = 32

os.makedirs(f"output/{ID}")

ROBLOX = OpenCloudClient(ROBLOX_API_KEY, ROBLOX_USER_ID, 15)

# Separate clients for imagery and terrain
IMAGERY_CLIENT = EOXClient(max_retries=15)
TERRAIN_CLIENT = AWSTerrainClient(max_retries=15)
# TERRAIN_CLIENT = MapboxClient(MAPBOX_API_KEY, max_retries=15)

# Terrain height encoding configuration

# AWS Terrarium
TERRAIN_ENCODING = {
    "coefficients": [256.0, 1.0, 1.0 / 256.0],
    "offset": -32768.0,
    "multiplier": 1.0,
}
TERRAIN_TILE_CONFIG = {
    "tileset_id": None,  # AWS doesn't use tileset IDs
    "file_format": ".png",
}

# Mapbox
# TERRAIN_ENCODING = {
#     "coefficients": [65536.0, 256.0, 1.0],
#     "offset": -10000.0,
#     "multiplier": 0.1,
# }
# TERRAIN_TILE_CONFIG = {
#     "tileset_id": "mapbox.mapbox-terrain-dem-v1",
#     "file_format": ".pngraw",
# }

AIRPORTS = airportsdata.load()


# Logging setup

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
stream.setFormatter(TerminalFormatter())

# Old FileHandler:
# fh = logging.FileHandler(LOGS_PATH) 

# New RotatingFileHandler:
# This will create log files up to 5MB, and keep the 4 last old files (20MB total).
fh = RotatingFileHandler(LOGS_PATH, maxBytes=5*1024*1024, backupCount=100)
fh.setLevel(logging.DEBUG)
fh.setFormatter(FileFormatter())

logger.addHandler(stream)
logger.addHandler(fh)

# Map Generation Settings

QUADTREE_ROOT = Tile(1543, 3212, 13)
QUADTREE_MAX_LOD = 13
QUADTREE_LOD_THRESHOLD = 13
QUADTREE_AIRPORTS = [
    # "KATL",  # Atlanta
    # "KLAX",  # Los Angeles
    # "KORD",  # Chicago
    # "KDFW",  # Dallas Fort Worth
    # "KDEN",  # Denver
    # "KJFK",  # John F. Kennedy (New York City)
    # "KSFO",  # San Francisco
    # "KSEA",  # Seattle-Tacoma
    # "KLAS",  # Harry Reid (Las Vegas)
    # "KMIA",  # Miami
]
