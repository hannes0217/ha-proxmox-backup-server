import aiohttp
import asyncio
import logging
import json

_LOGGER = logging.getLogger(__name__)

class PBSClient:
    def __init__(self, host, port, username, password, verify_ssl=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.url = f"https://{host}:{port}/api2/json"
        self.ticket = None
        self.csrf_token = None

    async def _authenticate(self, session):
        """Authenticate and get a ticket."""
        auth_url = f"{self.url}/access/ticket"
        data = {"username": self.username, "password": self.password}
        try:
            async with session.post(auth_url, data=data, ssl=self.verify_ssl) as response:
                if response.status == 200:
                    res_data = await response.json()
                    self.ticket = res_data["data"]["ticket"]
                    self.csrf_token = res_data["data"]["CSRFPreventionToken"]
                    return True
                else:
                    _LOGGER.error(f"Authentication failed: {response.status}")
                    return False
        except Exception as e:
            _LOGGER.error(f"Error during authentication: {e}")
            return False

    async def _api_call(self, method, endpoint, params=None):
        connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Try to use existing ticket or authenticate
            if not self.ticket:
                if not await self._authenticate(session):
                    return None

            headers = {
                "Cookie": f"PBSAuthCookie={self.ticket}",
                "CSRFPreventionToken": self.csrf_token if self.csrf_token else ""
            }

            async with session.request(method, f"{self.url}{endpoint}", headers=headers, params=params) as response:
                if response.status == 401: # Ticket might have expired
                    if await self._authenticate(session):
                        headers["Cookie"] = f"PBSAuthCookie={self.ticket}"
                        headers["CSRFPreventionToken"] = self.csrf_token
                        async with session.request(method, f"{self.url}{endpoint}", headers=headers, params=params) as retry_response:
                            if retry_response.status == 200:
                                return await retry_response.json()
                
                if response.status != 200:
                    _LOGGER.error(f"Error calling PBS API: {response.status} at {endpoint}")
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
        # Find the first node (usually localhost or the PVE node name)
        nodes = res.get("data", []) if res else []
        return nodes[0] if nodes else {}
