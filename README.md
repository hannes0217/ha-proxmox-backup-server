# Proxmox Backup Server Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
![Version](https://img.shields.io/badge/version-0.1.0-blue.svg?style=for-the-badge)

Custom integration to monitor and manage Proxmox Backup Server (PBS) from Home Assistant.

## Features
- **Automatic Datastore Discovery:** Automatically creates sensors for all configured datastores.
- **Datastore Metrics:** Monitor total size, used space, and usage percentage.
- **Node Monitoring:** Track CPU usage and system uptime.
- **Backup Status:** Dedicated sensor for the status of the last backup task.
- **Secure Setup:** Supports API Tokens and optional SSL verification (useful for self-signed certificates).
- **Asynchronous:** Built with `aiohttp` for optimal performance within Home Assistant.

## Installation

### HACS (Recommended)
1. Open **HACS** in your Home Assistant instance.
2. Go to **Integrations** -> **Custom Repositories** (top right menu).
3. Add `https://github.com/hannes0217/ha-proxmox-backup-server` with category **Integration**.
4. Click **Install**.
5. Restart Home Assistant.

### Manual
1. Download the `custom_components/proxmox_backup_server` folder.
2. Copy it into your Home Assistant `custom_components` directory.
3. Restart Home Assistant.

## Configuration
1. Go to **Settings** -> **Devices & Services**.
2. Click **Add Integration**.
3. Search for **Proxmox Backup Server**.
4. Enter your PBS host, port (default 8007), username (e.g., `root@pam`), and your **API Token ID** and **Token Secret**.

## Contributions
This repository is maintained by **Helfende Hand**. Contributions and issue reports are welcome!
