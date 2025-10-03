import unittest
from unittest.mock import patch, MagicMock
from custom_components.besmart.climate import Thermostat, Besmart
from homeassistant.components.climate.const import HVACMode, HVACAction

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = status_code == 200

    def json(self):
        return self.json_data

class TestBesmartThermostat(unittest.TestCase):
    def setUp(self):
        self.thermostat = Thermostat(
            name="Test Thermostat",
            username="test",
            password="test",
            room_name="test_room"
        )
        # Mock the Besmart class
        self.thermostat._besmart = MagicMock()

    def test_mode_5_should_be_off(self):
        # Simulate response with mode=5
        mock_data = {
            "error": 0,
            "mode": "5",
            "heating": "0",
            "tempUnit": "0",
            "season": "0",
            "tempNow": "20.0",
            "comfT": "21.0",
            "saveT": "19.0",
            "frostT": "5.0",
            "tempOut": "18.0",
            "bat": "1"
        }
        
        self.thermostat._besmart.roomByTherId.return_value = mock_data
        
        # Update the thermostat
        self.thermostat.update()
        
        # Check that HVAC mode is OFF
        self.assertEqual(self.thermostat.hvac_mode, HVACMode.OFF)
        self.assertEqual(self.thermostat.hvac_action, HVACAction.OFF)

    def test_mode_1_with_heating(self):
        # Simulate response with mode=1 and heating=1
        mock_data = {
            "error": 0,
            "mode": "1",
            "heating": "1",
            "tempUnit": "0",
            "season": "1",
            "tempNow": "20.0",
            "comfT": "21.0",
            "saveT": "19.0",
            "frostT": "5.0",
            "tempOut": "18.0",
            "bat": "1"
        }
        
        self.thermostat._besmart.roomByTherId.return_value = mock_data
        
        # Update the thermostat
        self.thermostat.update()
        
        # Check that HVAC mode is HEAT and action is HEATING
        self.assertEqual(self.thermostat.hvac_mode, HVACMode.HEAT)
        self.assertEqual(self.thermostat.hvac_action, HVACAction.HEATING)

    def test_season_0_should_be_off(self):
        # Simulate response with season=0
        mock_data = {
            "error": 0,
            "mode": "2",
            "heating": "0",
            "tempUnit": "0",
            "season": "0",
            "tempNow": "20.0",
            "comfT": "21.0",
            "saveT": "19.0",
            "frostT": "5.0",
            "tempOut": "18.0",
            "bat": "1"
        }
        
        self.thermostat._besmart.roomByTherId.return_value = mock_data
        
        # Update the thermostat
        self.thermostat.update()
        
        # Check that HVAC mode is OFF based on season
        self.assertEqual(self.thermostat.hvac_mode, HVACMode.OFF)

if __name__ == '__main__':
    unittest.main()