import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE, UnitOfInformation
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    entities = []
    
    # Add Datastore Sensors
    datastores = coordinator.data.get("datastores", {})
    for store_name in datastores:
        entities.append(PBSDatastoreSensor(coordinator, store_name, "used_percentage"))
        entities.append(PBSDatastoreSensor(coordinator, store_name, "total"))
        entities.append(PBSDatastoreSensor(coordinator, store_name, "used"))

    # Add Node Sensors
    entities.append(PBSNodeSensor(coordinator, "cpu", PERCENTAGE))
    entities.append(PBSNodeSensor(coordinator, "uptime", "s"))
    
    # Add Task Sensor (last backup)
    entities.append(PBSTaskSensor(coordinator, "last_backup"))

    async_add_entities(entities)

class PBSDatastoreSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, store_name, sensor_type):
        super().__init__(coordinator)
        self.store_name = store_name
        self.sensor_type = sensor_type
        self._attr_name = f"PBS {store_name} {sensor_type.replace('_', ' ').capitalize()}"
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_{store_name}_{sensor_type}"
        
        if sensor_type == "used_percentage":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type in ["total", "used"]:
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_state_class = SensorStateClass.MEASUREMENT

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

class PBSNodeSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type, unit):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_name = f"PBS Node {sensor_type.capitalize()}"
        self._attr_native_unit_of_measurement = unit
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_node_{sensor_type}"

    @property
    def native_value(self):
        node_data = self.coordinator.data.get("node", {})
        if self.sensor_type == "cpu":
            return round(node_data.get("cpu", 0) * 100, 2)
        return node_data.get(self.sensor_type)

class PBSTaskSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type):
        super().__init__(coordinator)
        self._attr_name = "PBS Last Backup Status"
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_last_backup"

    @property
    def native_value(self):
        tasks = self.coordinator.data.get("tasks", [])
        backup_tasks = [t for t in tasks if t.get("worker_type") == "backup"]
        if backup_tasks:
            return backup_tasks[0].get("status")
        return "Unknown"
