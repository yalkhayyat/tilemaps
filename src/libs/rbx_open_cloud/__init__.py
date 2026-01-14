import requests
from .open_cloud_constants import *
import json
import time
import logging


class OperationFailedException(Exception):
    def __init__(self, opId, error) -> None:
        super().__init__(f"Error while processing Operation: {opId}\nError: {error}")


class CreateAssetFailedException(Exception):
    def __init__(self, file, error) -> None:
        super().__init__(f"Error while creating Asset: {file}\nError: {error}")


class DatastoreOperationFailedException(Exception):
    def __init__(self, operation, error) -> None:
        super().__init__(
            f"Error while performing datastore operation: {operation}\nError: {error}"
        )


class OpenCloudClient:
    def __init__(
        self, api_key: str, user_id: str, max_retries: int, universe_id: str = None
    ) -> None:
        self.api_key = api_key
        self.user_id = user_id
        self.max_retries = max_retries
        self.universe_id = universe_id

    def CreateAsset(
        self,
        file_path: str,
        asset_type: str,
        content_type: str,
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
                OpenCloudAPI.ASSETS, headers=headers, data=data, files=files, timeout=60
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
                OpenCloudAPI.OPERATIONS + f"/{operationId}", headers=headers, timeout=60
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

    def GetDatastoreEntry(
        self, datastore_name: str, entry_key: str, scope: str = "global"
    ) -> dict | None:
        """Get a datastore entry. Returns the entry data or None if not found."""
        if not self.universe_id:
            raise ValueError("universe_id is required for datastore operations")

        headers = {
            "x-api-key": self.api_key,
        }

        url = f"{OpenCloudAPI.DATASTORES_BASE}/{self.universe_id}/standard-datastores/datastore/entries/entry"
        params = {
            "datastoreName": datastore_name,
            "entryKey": entry_key,
            "scope": scope,
        }

        for i in range(self.max_retries):
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.ok:
                try:
                    return json.loads(response.text)
                except json.JSONDecodeError:
                    # Return raw text if not JSON
                    return {"value": response.text}
            elif response.status_code == V1ErrorCodes.NOT_FOUND:
                return None
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for Get Datastore Entry. Trying again in 60 seconds."
                )
                time.sleep(60)
                i -= 1

            # extra timeout between retries
            time.sleep(i)

        raise DatastoreOperationFailedException(
            f"GetDatastoreEntry({datastore_name}, {entry_key})", response.text
        )

    def SetDatastoreEntry(
        self,
        datastore_name: str,
        entry_key: str,
        data: any,
        scope: str = "global",
        match_version: str = None,
        exclusive_create: bool = False,
    ) -> dict:
        """Set a datastore entry. Returns version information."""
        if not self.universe_id:
            raise ValueError("universe_id is required for datastore operations")

        headers = {"x-api-key": self.api_key, "content-type": "application/json"}

        if match_version:
            headers["roblox-entry-version"] = match_version

        if exclusive_create:
            headers["roblox-entry-create-only"] = "true"

        url = f"{OpenCloudAPI.DATASTORES_BASE}/{self.universe_id}/standard-datastores/datastore/entries/entry"
        params = {
            "datastoreName": datastore_name,
            "entryKey": entry_key,
            "scope": scope,
        }

        # Convert data to JSON string if it's not already a string
        if isinstance(data, (dict, list)):
            json_data = json.dumps(data)
        else:
            json_data = str(data)

        for i in range(self.max_retries):
            response = requests.post(
                url, headers=headers, params=params, data=json_data, timeout=60
            )

            if response.ok:
                return json.loads(response.text)
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for Set Datastore Entry. Trying again in 60 seconds."
                )
                time.sleep(60)
                i -= 1

            # extra timeout between retries
            time.sleep(i)

        raise DatastoreOperationFailedException(
            f"SetDatastoreEntry({datastore_name}, {entry_key})", response.text
        )

    def DeleteDatastoreEntry(
        self, datastore_name: str, entry_key: str, scope: str = "global"
    ) -> bool:
        """Delete a datastore entry. Returns True if successful."""
        if not self.universe_id:
            raise ValueError("universe_id is required for datastore operations")

        headers = {
            "x-api-key": self.api_key,
        }

        url = f"{OpenCloudAPI.DATASTORES_BASE}/{self.universe_id}/standard-datastores/datastore/entries/entry"
        params = {
            "datastoreName": datastore_name,
            "entryKey": entry_key,
            "scope": scope,
        }

        for i in range(self.max_retries):
            response = requests.delete(url, headers=headers, params=params, timeout=60)

            if response.ok:
                return True
            elif response.status_code == V1ErrorCodes.NOT_FOUND:
                return False
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for Delete Datastore Entry. Trying again in 60 seconds."
                )
                time.sleep(60)
                i -= 1

            # extra timeout between retries
            time.sleep(i)

        raise DatastoreOperationFailedException(
            f"DeleteDatastoreEntry({datastore_name}, {entry_key})", response.text
        )

    def ListDatastoreEntries(
        self,
        datastore_name: str,
        scope: str = "global",
        all_scopes: bool = False,
        prefix: str = "",
        limit: int = 10,
        cursor: str = "",
    ) -> dict:
        """List datastore entries. Returns a dictionary with entries and nextPageCursor."""
        if not self.universe_id:
            raise ValueError("universe_id is required for datastore operations")

        headers = {
            "x-api-key": self.api_key,
        }

        url = f"{OpenCloudAPI.DATASTORES_BASE}/{self.universe_id}/standard-datastores/datastore/entries"
        params = {
            "datastoreName": datastore_name,
            "scope": scope,
            "allScopes": str(all_scopes).lower(),
            "prefix": prefix,
            "limit": limit,
        }

        if cursor:
            params["cursor"] = cursor

        for i in range(self.max_retries):
            response = requests.get(url, headers=headers, params=params, timeout=60)

            if response.ok:
                return json.loads(response.text)
            elif (
                response.status_code == V1ErrorCodes.RESOURCE_EXHAUSTED
                or response.status_code == 0
            ):
                logging.warning(
                    "Exhausted Rate Limit for List Datastore Entries. Trying again in 60 seconds."
                )
                time.sleep(60)
                i -= 1

            # extra timeout between retries
            time.sleep(i)

        raise DatastoreOperationFailedException(
            f"ListDatastoreEntries({datastore_name})", response.text
        )
