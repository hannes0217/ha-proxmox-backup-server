import logging
from datetime import datetime
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
        entities.append(PBSGCSensor(coordinator, store_name, "removed_bytes"))

    # Node Sensors
    entities.append(PBSNodeSensor(coordinator, "cpu", PERCENTAGE))
    
    # Task Sensors
    entities.append(PBSTaskSensor(coordinator, "last_backup_status"))
    entities.append(PBSTaskSensor(coordinator, "last_backup_time"))
    entities.append(PBSTaskSensor(coordinator, "last_gc_status"))
    entities.append(PBSTaskSensor(coordinator, "last_verify_status"))

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
            # Back to Bytes to preserve native data class, but setting device_class for HA scaling
            self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
            self._attr_device_class = SensorDeviceClass.DATA_SIZE
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        data = self.coordinator.data["datastores"].get(self.store_name, {}).get("status")
        if not data:
            return None
        
        raw_value = data.get(self.sensor_type)
        if raw_value is None:
            return None

        if self.sensor_type == "used_percentage":
            total = data.get("total", 0)
            used = data.get("used", 0)
            return round((used / total * 100), 2) if total > 0 else 0
        
        return raw_value

class PBSGCSensor(PBSBaseEntity, SensorEntity):
    """Garbage Collection Sensors."""
    def __init__(self, coordinator, store_name, sensor_type):
        super().__init__(coordinator)
        self.store_name = store_name
        self._attr_name = f"{store_name} GC Removed"
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_{store_name}_gc_removed"
        self._attr_native_unit_of_measurement = UnitOfInformation.BYTES
        self._attr_device_class = SensorDeviceClass.DATA_SIZE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:delete-sweep"
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        gc_data = self.coordinator.data["datastores"].get(self.store_name, {}).get("gc")
        if not gc_data:
            return None
        return gc_data.get("removed-bytes")

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

    @property
    def native_value(self):
        node_data = self.coordinator.data.get("node", {})
        if self.sensor_type == "cpu":
            return round(node_data.get("cpu", 0) * 100, 2)
        return node_data.get(self.sensor_type)

class PBSTaskSensor(PBSBaseEntity, SensorEntity):
    def __init__(self, coordinator, sensor_type):
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        
        names = {
            "last_backup_status": "Last Backup Status",
            "last_backup_time": "Last Backup Time",
            "last_gc_status": "Last GC Status",
            "last_verify_status": "Last Verify Status"
        }
        self._attr_name = names.get(sensor_type, sensor_type.replace('_', ' ').capitalize())
        self._attr_unique_id = f"pbs_{coordinator.config_entry.data['host']}_{sensor_type}"
        
        if sensor_type == "last_backup_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_icon = "mdi:clock-check"
        elif "status" in sensor_type:
            self._attr_icon = "mdi:shield-check" if "verify" in sensor_type else "mdi:backup-restore"
        else:
            self._attr_icon = "mdi:history"

    @property
    def native_value(self):
        tasks = self.coordinator.data.get("tasks", [])
        
        if self.sensor_type in ["last_backup_status", "last_backup_time"]:
            target_type = "backup"
        elif self.sensor_type == "last_gc_status":
            target_type = "garbage_collection"
        elif self.sensor_type == "last_verify_status":
            target_type = "verify"
        else:
            return None

        # Sort tasks by starttime to get the absolute newest one
        filtered_tasks = sorted(
            [t for t in tasks if t.get("worker_type") == target_type and t.get("endtime") is not None],
            key=lambda x: x.get("starttime", 0),
            reverse=True
        )
        
        if not filtered_tasks:
            return "None" if "status" in self.sensor_type else None
            
        last_task = filtered_tasks[0]
        if "status" in self.sensor_type:
            return last_task.get("status")
        elif "time" in self.sensor_type:
            return datetime.fromtimestamp(last_task.get("starttime"))
