import logging
from datetime import datetime, timedelta
import requests
import voluptuous as vol

from homeassistant.components.climate import (
    PLATFORM_SCHEMA,
    ClimateEntity,
)
from homeassistant.components.climate.const import (
    HVACMode,
    HVACAction,
    ClimateEntityFeature,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_HIGH,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_ROOM,
    CONF_USERNAME,
    UnitOfTemperature,
)
import homeassistant.helpers.config_validation as cv


from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    """Set up BeSmart climate entity from a config entry."""
    ther_id = entry.data.get("ther_id")
    room_name = entry.data.get("room_name", "casa")

    besmart = Besmart(username="riccardodori", password="Ricky.Smart")
    besmart.login()
    room = besmart.roomByTherId(ther_id, room_name)

    async_add_entities([BeSmartClimate(besmart, room, room_name)])

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "BeSmart Thermostat"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_ROOM): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    thermostat = Thermostat(
        config.get(CONF_NAME),
        config.get(CONF_USERNAME),
        config.get(CONF_PASSWORD),
        config.get(CONF_ROOM),
    )
    add_entities([thermostat], True)
class Besmart:
    BASE_URL = "http://www.besmart-home.com/Android_vokera_20160516/"
    LOGIN = "login.php"
    ROOM_LIST = "getRoomList.php?deviceId={0}"
    ROOM_DATA = "getRoomData196.php?therId={0}&deviceId={1}"
    ROOM_MODE = "setRoomMode.php"
    ROOM_TEMP = "setRoomTemp.php"
    ROOM_CONF_TEMP = "setComfTemp.php"
    ROOM_ECON_TEMP = "setEconTemp.php"
    ROOM_FROST_TEMP = "setFrostTemp.php"
    GET_SETTINGS = "getSetting.php"
    SET_SETTINGS = "setSetting.php"

    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._device = None
        self._rooms = None
        self._lastupdate = None
        self._timeout = 30
        self._s = requests.Session()

    def login(self):
        try:
            resp = self._s.post(
                self.BASE_URL + self.LOGIN,
                data={"un": self._username, "pwd": self._password, "version": "32"},
                timeout=self._timeout,
            )
            _LOGGER.debug("Login response: %s", self._device)
            if resp.ok:
                self._device = resp.json()
        except Exception as ex:
            _LOGGER.warning("Login failed: %s", ex)
            self._device = None

    def rooms(self):
        if not self._device:
            self.login()
        try:
            if self._device:
                resp = self._s.post(
                    self.BASE_URL + self.ROOM_LIST.format(self._device.get("deviceId")),
                    timeout=self._timeout,
                )
                _LOGGER.debug("Room list response: %s", resp.text)
                if resp.ok:
                    self._lastupdate = datetime.now()
                    self._rooms = {
                        y.get("name").lower(): y
                        for y in filter(lambda x: x.get("id") is not None, resp.json())
                    }
                    return self._rooms
        except Exception as ex:
            _LOGGER.warning("Room fetch failed: %s", ex)
            self._device = None
        return None

    def roomdata(self, room):
        if room is None:
            _LOGGER.warning("roomdata called with None room")
            return None
        self.login()
        try:
            if self._device:
                resp = self._s.get(
                    self.BASE_URL + self.ROOM_DATA.format(
                        room.get("therId"), self._device.get("deviceId")
                    ) + "&boilerIsConnected=1",
                    timeout=self._timeout,
                )
                if resp.ok:
                    return resp.json()
        except Exception as ex:
            _LOGGER.warning("roomdata error: %s", ex)
            self._device = None
        return None

    def roomByTherId(self, therId, name=""):
        """Recupera i dati stanza direttamente tramite therId, ignorando il nome stanza."""
        if not self._device:
            self.login()
    
        room = {"therId": therId, "name": name}
        return self.roomdata(room)

    def setRoomMode(self, room_name, mode):
        room = self.roomByTherId(room_name, "casa")
        if self._device and room:
            data = {
                "deviceId": self._device.get("deviceId"),
                "therId": room.get("roomMark"),
                "mode": mode,
            }
            resp = self._s.post(self.BASE_URL + self.ROOM_MODE, data=data, timeout=self._timeout)
            if resp.ok:
                msg = resp.json()
                _LOGGER.debug("setRoomMode response: %s", msg)
                if msg.get("error") == 1:
                    return True
        return None

    def setRoomTemp(self, room_name, new_temp, url=None):
        url = url or self.ROOM_TEMP
        room = self.roomByTherId(room_name, "casa")
        if room and self._device and self._device.get("deviceId"):
            new_temp = round(new_temp, 1)
            if room.get("tempUnit") in {"N/A", "0"}:
                tpCInt, tpCIntFloat = str(new_temp).split(".")
            else:
                tpCInt, tpCIntFloat = str(round((new_temp - 32.0) / 1.8, 1)).split(".")
            data = {
                "deviceId": self._device.get("deviceId"),
                "therId": room.get("roomMark"),
                "tempSet": tpCInt,
                "tempSetFloat": tpCIntFloat,
            }
            resp = self._s.post(self.BASE_URL + url, data=data, timeout=self._timeout)
            if resp.ok:
                msg = resp.json()
                _LOGGER.debug("setRoomTemp response: %s", msg)
                if msg.get("error") == 1:
                    return True
        else:
            _LOGGER.warning("Room not found or device missing for: %s", room_name)
        return None

    def setRoomConfortTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_CONF_TEMP)

    def setRoomECOTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_ECON_TEMP)

    def setRoomFrostTemp(self, room_name, new_temp):
        return self.setRoomTemp(room_name, new_temp, self.ROOM_FROST_TEMP)

    def getSettings(self, room_name):
        room = self.roomByTherId(room_name, "casa")
        if self._device and room:
            data = {
                "deviceId": self._device.get("deviceId"),
                "therId": room.get("roomMark"),
            }
            resp = self._s.post(self.BASE_URL + self.GET_SETTINGS, data=data, timeout=self._timeout)
            if resp.ok:
                msg = resp.json()
                _LOGGER.debug("getSettings response: %s", msg)
                if msg.get("error") == 0:
                    return msg
        return None

    def setSettings(self, room_name, season):
        room = self.roomByTherId(room_name, "casa")
        if self._device and room:
            old_data = self.getSettings(room_name)
            if old_data and old_data.get("error") == 0:
                min_ip, min_fp = str(old_data.get("minTempSetPoint", "30.0")).split(".")
                max_ip, max_fp = str(old_data.get("maxTempSetPoint", "30.0")).split(".")
                curve_ip, curve_fp = str(old_data.get("tempCurver", "0.0")).split(".")
                data = {
                    "deviceId": self._device.get("deviceId"),
                    "therId": room.get("roomMark"),
                    "minTempSetPointIP": min_ip,
                    "minTempSetPointFP": min_fp,
                    "maxTempSetPointIP": max_ip,
                    "maxTempSetPointFP": max_fp,
                    "sensorInfluence": old_data.get("sensorInfluence", "0"),
                    "tempCurveIP": curve_ip,
                    "tempCurveFP": curve_fp,
                    "unit": old_data.get("unit", "0"),
                    "season": season,
                    "boilerIsOnline": old_data.get("boilerIsOnline", "0"),
                }
                resp = self._s.post(self.BASE_URL + self.SET_SETTINGS, data=data, timeout=self._timeout)
                if resp.ok:
                    msg = resp.json()
                    _LOGGER.debug("setSettings response: %s", msg)
                    if msg.get("error") == 0:
                        return msg
        return None
class Thermostat(ClimateEntity):
    def __init__(self, name, username, password, room_name):
        self._name = name
        self._username = username
        self._password = password
        self._room_name = room_name
        self._besmart = Besmart(username, password)
    
        # Temperature values
        self._comfT = None
        self._econT = None
        self._frostT = None
        self._target_temp = None
        self._target_temp_low = None
        self._target_temp_high = None
        self._current_temperature = None
    
        # HVAC and preset states
        self._hvac_mode = HVACMode.OFF
        self._hvac_action = HVACAction.OFF
        self._preset_mode = "comfort"
        self._preset_modes = ["comfort", "eco", "frost"]
        self._available_modes = [HVACMode.HEAT, HVACMode.OFF]
    
        # Internal state tracking
        self._last_update = None
        self._battery = False
        self._heating_state = False
        self._current_state = 2
        self._current_unit = "0"
        self._season = "1"
        self._tempSetMark = "2"
    
        # Mapping dictionaries
        self.PRESET_HA_TO_BESMART = {"comfort": "2", "eco": "1", "frost": "0"}
        self.PRESET_BESMART_TO_HA = {"2": "comfort", "1": "eco", "0": "frost"}
        self.HVAC_MODE_HA_BESMART = {HVACMode.HEAT: "1", HVACMode.OFF: "0"}
        self.HVAC_MODE_BESMART_TO_HA = {"1": HVACMode.HEAT, "0": HVACMode.OFF}
        self.HVAC_MODE_LIST = [HVACMode.HEAT, HVACMode.OFF]
        self.PRESET_MODE_LIST = ["comfort", "eco", "frost"]
    
        # Supported features
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE |
            ClimateEntityFeature.TARGET_TEMPERATURE_RANGE |
            ClimateEntityFeature.PRESET_MODE
        )

    @property
    def unique_id(self):
        return f"besmart_{self._room_name}"


    @property
    def name(self):
        return self._name

    @property
    def temperature_unit(self):
        return UnitOfTemperature.CELSIUS if self._current_unit == "0" else UnitOfTemperature.FAHRENHEIT

    @property
    def current_temperature(self):
        return self._current_temperature

    @property
    def target_temperature(self):
        return self._target_temp

    @property
    def target_temperature_low(self):
        return self._target_temp_low

    @property
    def target_temperature_high(self):
        return self._target_temp_high

    @property
    def hvac_mode(self):
        return self.HVAC_MODE_BESMART_TO_HA.get(self._season, HVACMode.OFF)

    @property
    def hvac_action(self):
        if self._heating_state:
            return HVACAction.HEATING if self.hvac_mode == HVACMode.HEAT else HVACAction.COOLING
        return HVACAction.OFF

    @property
    def preset_mode(self):
        return self.PRESET_BESMART_TO_HA.get(str(self._current_state), "comfort")

    @property
    def preset_modes(self):
        return self.PRESET_MODE_LIST

    @property
    def hvac_modes(self):
        return self.HVAC_MODE_LIST
    def set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE)
        target_temp_high = kwargs.get(ATTR_TARGET_TEMP_HIGH)
        target_temp_low = kwargs.get(ATTR_TARGET_TEMP_LOW)

        _LOGGER.debug(
            "Set temperature: Frost=%s Eco=%s Comfort=%s",
            temperature, target_temp_low, target_temp_high
        )

        if temperature is not None:
            self._besmart.setRoomConfortTemp(self._room_name, temperature)

        if temperature is not None:
            self._besmart.setRoomConfortTemp(self._room_name, temperature)
            self._target_temp = temperature  # ← aggiorna lo stato interno


        if target_temp_low is not None:
            self._besmart.setRoomECOTemp(self._room_name, target_temp_low)

    def set_preset_mode(self, preset_mode):
        mode = self.PRESET_HA_TO_BESMART.get(preset_mode, "2")
        self._besmart.setRoomMode(self._room_name, mode)
        _LOGGER.debug("Set preset_mode: %s (%s)", preset_mode, mode)

    def set_hvac_mode(self, hvac_mode):
        mode = self.HVAC_MODE_HA_BESMART.get(hvac_mode)
        self._besmart.setSettings(self._room_name, mode)
        _LOGGER.debug("Set hvac_mode: %s (%s)", hvac_mode, mode)

    def update(self):
        _LOGGER.debug("🔄 Update called for room: %s", self._room_name)
        data = self._besmart.roomByTherId(self._room_name, "casa")
    
        if not data or data.get("error") != 0:
            _LOGGER.warning("⚠️ No valid data received for room: %s", self._room_name)
            return
    
        # 🔢 Program parsing
        try:
            today = datetime.today().isoweekday() % 7
            index = datetime.today().hour * 2 + (1 if datetime.today().minute > 30 else 0)
            programWeek = data.get("programWeek", [])
            self._tempSetMark = programWeek[today][index] if programWeek else "2"
        except Exception as ex:
            _LOGGER.warning("Program parsing error: %s", ex)
            self._tempSetMark = "2"
    
        # 🔋 Battery status
        try:
            self._battery = not bool(int(data.get("bat", "0")))
        except (TypeError, ValueError):
            self._battery = False
    
        # 🌡️ Temperature parsing
        def safe_float(value, fallback):
            try:
                return float(value)
            except (TypeError, ValueError):
                return fallback
    
        self._frostT = safe_float(data.get("frostT"), 5.0)
        self._econT = safe_float(data.get("saveT"), 16.0)
        self._comfT = safe_float(data.get("comfT"), 20.0)
        self._current_temperature = safe_float(data.get("tempNow"), 20.0)
        self._target_temp = self._comfT
        self._temp_outdoor = safe_float(data.get("tempOut"), 20.0)
        self._target_temp_low = self._econT
        self._target_temp_high = self._comfT

    
        # 🔥 Heating state
        self._heating_state = data.get("heating") == "1"
    
        # 🎛️ HVAC mode mapping
        try:
            self._current_state = int(data.get("mode", "2"))
        except (TypeError, ValueError):
            self._current_state = 2
    
        if self._current_state == 5:
            self._hvac_mode = HVACMode.OFF
            self._hvac_action = HVACAction.OFF
        elif self._current_state == 1:
            self._hvac_mode = HVACMode.HEAT
            self._hvac_action = HVACAction.HEATING if self._heating_state else HVACAction.IDLE
        else:
            self._hvac_mode = HVACMode.HEAT
            self._hvac_action = HVACAction.IDLE
    
        # 🌡️ Unit and season
        self._current_unit = data.get("tempUnit", "0")
        self._season = data.get("season", "1")
    
        # 🧊 Preset mode mapping
        if self._tempSetMark == "1":
            self._preset_mode = "eco"
        elif self._tempSetMark == "2":
            self._preset_mode = "comfort"
        elif self._tempSetMark == "3":
            self._preset_mode = "frost"
        else:
            self._preset_mode = "comfort"
    
        _LOGGER.debug("✅ Update complete: tempNow=%.1f, tempOut=%.1f, hvac_mode=%s, preset=%s",
                      self._current_temperature, self._temp_outdoor, self._hvac_mode, self._preset_mode)

    @property
    def extra_state_attributes(self):
        return {
            "battery_state": self._battery,
            "frost_temperature": self._frostT,
            "eco_temperature": self._econT,
            "comfort_temperature": self._comfT,
            "season_mode": self.hvac_mode,
            "heating_state": self._heating_state,
            "preset_mark": self._tempSetMark,
            "tempOut": self._temp_outdoor,  # ← nuovo attributo
        }
