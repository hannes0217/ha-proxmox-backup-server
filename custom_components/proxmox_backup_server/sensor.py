import logging
from homeassistant.components.sensor import (
    SensorEntity, 
    SensorDeviceClass, 
    SensorStateClass,
    EntityCategory
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    PERCENTAGE, 
    UnitOfInformation, 
    UnitOfTime
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Datastores
    datastores = coordinator.data.get("datastores", {})
    for store_name in datastores:
        entities.append(PBSDatastoreSensor(coordinator, store_name, "used_percentage"))
        entities.append(PBSDatastoreSensor(coordinator, store_name, "total"))
        entities.append(PBSDatastoreSensor(coordinator, store_name, "used"))
        entities.append(PBSDatastoreSensor(coordinator, store_name, "avail"))

    # Node Sensors
    entities.append(PBSNodeSensor(coordinator, "cpu", PERCENTAGE))
    entities.append(PBSNodeSensor(coordinator, "uptime", UnitOfTime.SECONDS))
    
    # Task Sensor
    entities.append(PBSTaskSensor(coordinator, "last_backup"))

    async_add_entities(entities)

class PBSBaseEntity(CoordinatorEntity):
    """Base class for PBS entities."""
    
    def __init__(self, coordinator):
        super().__init__(coordinator)
        host = coordinator.config_entry.data["host"]
        self._attr_device_info = {
            "identifiers": {(DOMAIN, host)},
            "name": f"Proxmox Backup Server ({host})",
            "manufacturer": "Proxmox",
            "model": "Backup Server",
            "configuration_url": f"https://{host}:{coordinator.config_entry.data.get('port', 8007)}",
        }

class PBSDatastoreSensor(PBSBaseEntity, SensorEntity):
    def __init__(self, coordinator, store_name, sensor_type):
        super().__init__(coordinator)
        self.store_name = store_name
        self.sensor_type = sensor_type
        self._attr_name = f"{store_name} {sensor_type.replace('_', ' ').capitalize()}"
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_{store_name}_{sensor_type}"
        
        if sensor_type == "used_percentage":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:chart-donut"
        elif sensor_type in ["total", "used", "avail"]:
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            # Suggesting GB/TB for the UI but keeping BYTES as native unit for HA to scale automatically
            self._attr_suggested_unit_of_measurement = UnitOfInformation.GIGABYTES

    @property
    def native_value(self):
        data = self.coordinator.data["datastores"].get(self.store_name)
        if not data:
            return None
        
        if self.sensor_type == "used_percentage":
            total = data.get("total", 0)
            used = data.get("used", 0)
            return round((used / total * 100), 2) if total > 0 else 0
        
        return data.get(self.sensor_type)

class PBSNodeSensor(PBSBaseEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type, unit):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_name = f"Node {sensor_type.capitalize()}"
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_node_{sensor_type}"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        
        if sensor_type == "cpu":
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_icon = "mdi:cpu-64-bit"
        elif sensor_type == "uptime":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self):
        node_data = self.coordinator.data.get("node", {})
        if self.sensor_type == "cpu":
            return round(node_data.get("cpu", 0) * 100, 2)
        return node_data.get(self.sensor_type)

class PBSTaskSensor(PBSBaseEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type):
        super().__init__(coordinator)
        self._attr_name = "Last Backup Status"
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_last_backup"
        self._attr_icon = "mdi:backup-restore"

    @property
    def native_value(self):
        tasks = self.coordinator.data.get("tasks", [])
        backup_tasks = [t for t in tasks if t.get("worker_type") == "backup"]
        if backup_tasks:
            return backup_tasks[0].get("status")
        return "Unknown"
