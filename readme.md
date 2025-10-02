# BeSmart Thermostat for Home Assistant

Support for Riello's BeSmart thermostats, now updated for compatibility with **Home Assistant 2025.1**.

This custom integration allows you to control your BeSmart thermostat directly from Home Assistant, including temperature adjustment, preset modes, and HVAC state monitoring.

> ⚠️ **Note:** In the configuration, the `room` parameter refers to the thermostat's unique `therId`, not the room name.

---

## 🆕 What's new in v0.2

- ✅ Full compatibility with Home Assistant 2025.1
- ✅ Support for UI-based configuration via `config_flow`
- ✅ Interactive temperature control via climate entity
- ✅ Unique ID support for entity customization
- ✅ Improved parsing and error handling
- ✅ Preset modes: `comfort`, `eco`, `frost`

---

## 🔧 Configuration example (manual YAML)

```yaml
climate:
  - platform: besmart
    name: Besmart Thermostat
    username: <your-username>
    password: <your-password>
    room: <therId>  # ← This is the unique thermostat ID
    scan_interval: 10
