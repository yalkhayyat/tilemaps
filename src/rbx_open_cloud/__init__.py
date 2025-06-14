import requests
from rbx_open_cloud.open_cloud_constants import *
import json
import time
import logging


class OperationFailedException(Exception):
    def __init__(self, opId, error) -> None:
        super().__init__(f"Error while processing Operation: {opId}\nError: {error}")


class CreateAssetFailedException(Exception):
    def __init__(self, file, error) -> None:
        super().__init__(f"Error while creating Asset: {file}\nError: {error}")


class OpenCloudClient:
    def __init__(self, api_key: str, user_id: str, max_retries: int) -> None:
        self.api_key = api_key
        self.user_id = user_id
        self.max_retries = max_retries

    def CreateAsset(
        self,
        file_path: str,
        asset_type: AssetType,
        content_type: ContentType,
        display_name: str,
        description: str = "",
    ) -> str | None:
        """Send a 'Create Asset' POST Request. Returns the Operation ID."""
        headers = {
            "x-api-key": self.api_key,
        }

        data = {
            "request": json.dumps(
                {
                    "assetType": asset_type,
                    "displayName": display_name,
                    "description": description,
                    "creationContext": {
                        "creator": {
                            "userId": self.user_id,
                        }
                    },
                }
            )
        }

        files = {"fileContent": (file_path, open(file_path, "rb"), content_type)}

        for i in range(self.max_retries):
            response = requests.post(
                OpenCloudAPI.ASSETS,
                headers=headers,
                data=data,
                files=files,
                timeout=60
            )

            if response.ok:
                return json.loads(response.text)["operationId"]
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for Create Asset. Trying again in 60 seconds"
                )
                # Avoid hitting the rate limit if exhausted, or wait extra time if no response recieved
                time.sleep(60)
                # Try one more time
                i -= 1

        raise CreateAssetFailedException(file_path, response.text)

    def GetOperation(self, operationId: str) -> str | None:
        headers = {
            "x-api-key": self.api_key,
        }

        for i in range(self.max_retries):
            response = requests.get(
                OpenCloudAPI.OPERATIONS + f"/{operationId}",
                headers=headers,
                timeout=60
            )

            if response.ok:
                data = json.loads(response.text)

                if "error" in data.keys():
                    raise OperationFailedException(operationId, data["error"])

                if data["done"]:
                    return data["response"]["assetId"]
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for Get Operation. Trying again in 60 seconds."
                )
                # Avoid hitting the rate limit if exhausted, or wait extra time if no response recieved
                time.sleep(60)
                # Try one more time
                i -= 1

            # extra timeout between retries
            time.sleep(i)

        raise OperationFailedException(operationId, response.text)
