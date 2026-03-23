import aiohttp
import asyncio
import logging
import urllib3
import json

_LOGGER = logging.getLogger(__name__)

class PBSClient:
    def __init__(self, host, port, username, token_id, token_secret, verify_ssl=False):
        self.host = host
        self.port = port
        self.username = username
        self.token_id = token_id
        self.token_secret = token_secret
        self.verify_ssl = verify_ssl
        self.url = f"https://{host}:{port}/api2/json"
        # PBS format: PBSAPIToken=USER!TOKENID:SECRET
        self.auth_header = f"PBSAPIToken={username}!{token_id}:{token_secret}"

    async def _api_call(self, method, endpoint, params=None):
        headers = {"Authorization": self.auth_header}
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.request(method, f"{self.url}{endpoint}", headers=headers, params=params) as response:
                if response.status != 200:
                    _LOGGER.error(f"Error calling PBS API: {response.status}")
                    return None
                return await response.json()

    async def get_datastores(self):
        res = await self._api_call("GET", "/admin/datastore")
        return res.get("data", []) if res else []

    async def get_datastore_status(self, store):
        res = await self._api_call("GET", f"/admin/datastore/{store}/status")
        return res.get("data") if res else None

    async def get_tasks(self, limit=5):
        params = {"limit": limit, "all": 1}
        res = await self._api_call("GET", "/nodes/localhost/tasks", params=params)
        return res.get("data", []) if res else []

    async def get_node_status(self):
        res = await self._api_call("GET", "/nodes")
        return res.get("data", [{}])[0] if res else {}
