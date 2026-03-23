import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from datetime import timedelta
from .const import DOMAIN, UPDATE_INTERVAL, CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_TOKEN_ID, CONF_TOKEN_SECRET, CONF_VERIFY_SSL
from .api import PBSClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    user = entry.data[CONF_USERNAME]
    token_id = entry.data[CONF_TOKEN_ID]
    secret = entry.data[CONF_TOKEN_SECRET]
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, False)

    client = PBSClient(host, port, user, token_id, secret, verify_ssl)
    
    async def async_update_data():
        try:
            datastores = await client.get_datastores()
            ds_data = {}
            for ds in datastores:
                store = ds["store"]
                ds_data[store] = await client.get_datastore_status(store)
            
            return {
                "datastores": ds_data,
                "node": await client.get_node_status(),
                "tasks": await client.get_tasks()
            }
        except Exception as err:
            raise UpdateFailed(f"Error communicating with PBS API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"PBS {host}",
        update_method=async_update_data,
        update_interval=timedelta(seconds=UPDATE_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
