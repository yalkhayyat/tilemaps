from enum import IntEnum
from strenum import StrEnum

class ContentType(StrEnum):
    MP3 = "audio/mpeg"
    OGG = "audio/ogg"
    PNG = "image/png"
    JPEG = "image/jpeg"
    BMP = "image/bmp"
    TGA = "image/tga"
    FBX = "model/fbx"
    MP4 = "video/mp4"
    MOV = "video/mov"


class AssetType(StrEnum):
    AUDIO = "Audio"
    DECAL = "Decal"
    MODEL = "Model"
    VIDEO = "Video"
    IMAGE = "Image"
    MESH = "Mesh"


class V1ErrorCodes(IntEnum):
    # 400 - INVALID_ARGUMENT: You passed an invalid argument, such as an invalid universeId.
    # You might also have missing or invalid headers, such as Content-Length and Content-Type.
    INVALID_ARGUMENT = 400

    # 403 - INSUFFICIENT_SCOPE: The request requires higher privileges than provided by the access token.
    INSUFFICIENT_SCOPE = 403

    # 403 - PERMISSION_DENIED: Your request doesn't have sufficient scope to perform the operation.
    PERMISSION_DENIED = 403

    # 404 - NOT_FOUND: The system can't find your specified resources, such as a data store.
    NOT_FOUND = 404

    # 409 - ABORTED: The operation was aborted due to a conflict, such as publishing a place that is not part of the universe.
    ABORTED = 409

    # 429 - RESOURCE_EXHAUSTED: You don't have enough quota to perform the operation, typically due to sending too many requests.
    RESOURCE_EXHAUSTED = 429

    # 499 - CANCELLED: The system terminates the request, typically due to a client-side timeout.
    CANCELLED = 499

    # 500 - INTERNAL: Internal server error. Typically a server bug.
    INTERNAL = 500

    # 501 - NOT_IMPLEMENTED: The server doesn't implement the API method.
    NOT_IMPLEMENTED = 501

    # 503 - UNAVAILABLE: Service unavailable. Typically the server is down.
    UNAVAILABLE = 503


class OpenCloudAPI(StrEnum):
    ASSETS = "https://apis.roblox.com/assets/v1/assets"
    OPERATIONS = "https://apis.roblox.com/assets/v1/operations"
    DATASTORES_BASE = "https://apis.roblox.com/datastores/v1/universes"
