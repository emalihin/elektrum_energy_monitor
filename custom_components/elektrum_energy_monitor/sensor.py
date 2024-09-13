import logging
from datetime import datetime, timedelta
import requests
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.event import async_track_time_change
from .const import DOMAIN, LOGIN_URL, AUTH_URL, DATA_URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Elektrum Energy Monitor sensor based on a config entry."""
    username = config_entry.data["username"]
    password = config_entry.data["password"]

    # Create the sensor entity
    sensor = ElektrumEnergyMonitorSensor(username, password)

    # Add the sensor entity to Home Assistant
    async_add_entities([sensor], update_before_add=True)

    # Schedule the daily update at 10 AM
    async_track_time_change(hass, sensor.update, hour=10, minute=0, second=0)


class ElektrumEnergyMonitorSensor(SensorEntity):
    """Representation of the Elektrum Energy Monitor sensor."""

    def __init__(self, username, password):
        """Initialize the sensor."""
        self._name = "Elektrum Energy Monitor"
        self._state = None
        self._username = username
        self._password = password
        self._unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_state_class = (
            "measurement"  # Using measurement for fluctuating hourly data
        )
        self._attr_device_class = "energy"
        self._attr_extra_state_attributes = {}  # Initialize the attributes
        self.hourly_usage = {}
        self._unique_id = (
            f"elektrum_energy_monitor_{username}"  # Unique ID for the sensor
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the total energy consumption for the previous day."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of the sensor."""
        return self._unit_of_measurement

    @property
    def state_class(self):
        """Return the state class for fluctuating hourly energy usage."""
        return "measurement"  # Use measurement for fluctuating hourly data

    @property
    def device_class(self):
        """Return the device class for energy monitoring."""
        return "energy"

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    def update(self):
        """Update the sensor by querying Elektrum's API and processing hourly data for yesterday."""
        session = requests.Session()

        # Get the previous day's date in YYYY-M-D format
        previous_day = datetime.now() - timedelta(days=1)
        fromDate = previous_day.strftime("%Y-%-m-%-d")

        # Form the URL with the fromDate parameter
        api_url = f"{DATA_URL}?step=D&fromDate={fromDate}"

        # Perform login and get authentication token
        token = self.get_auth_token(session)
        if not token:
            _LOGGER.error("Failed to retrieve authentication token.")
            return None

        # Authenticate
        if not self.authenticate(token, session):
            _LOGGER.error("Authentication failed.")
            return None

        # Fetch the data
        response = session.get(api_url)
        if response.status_code == 200:
            data = response.json()
            self.process_hourly_data(data, previous_day)
        else:
            _LOGGER.error(
                "Failed to fetch energy data. HTTP Status %d", response.status_code
            )

    def extract_all(self, text, start_str, end_str, inclusive=False):
        """Utility function to extract tokens from HTML."""
        results = []
        start = 0
        while True:
            start = text.find(start_str, start)
            if start == -1:
                break
            start += len(start_str)
            end = text.find(end_str, start)
            if end == -1:
                break
            if inclusive:
                results.append(text[start - len(start_str) : end + len(end_str)])
            else:
                results.append(text[start:end])
        return results

    def get_auth_token(self, session):
        """Retrieve the authentication token needed for logging in."""
        headers = {
            "User-Agent": "home-assistant",
        }
        r1 = session.get(AUTH_URL, headers=headers, allow_redirects=True)
        if r1.status_code == 200:
            tokens = self.extract_all(r1.text, 'data-token="', '"', inclusive=False)
            return tokens[1] if tokens else None
        else:
            return None

    def authenticate(self, token, session):
        """Authenticate using the token."""
        login_params = {
            "email": self._username,
            "password": self._password,
            "captcha": "",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:77.0) Gecko/20100101 Firefox/77.0",
        }
        r3 = session.post(LOGIN_URL, data=login_params, headers=headers)
        return r3.status_code == 200

    def process_hourly_data(self, data, previous_day):
        """Process the hourly energy data and append it to the existing data."""
        hourly_data = data.get("data", {}).get("A+", [])

        if not hourly_data:
            _LOGGER.error("No consumption data found!")
            return

        # Store hourly data for the current day
        hourly_consumption = {}
        total_consumption = 0

        for item in hourly_data:
            hour_str = item.get("date", "")  # Example: "01:00", "02:00"
            consumption_value = list(item.values())[
                1
            ]  # Get the consumption value for this hour
            hourly_consumption[hour_str] = consumption_value
            total_consumption += consumption_value  # Accumulate total consumption

        # Retrieve existing historical data (if any)
        historical_data = self._attr_extra_state_attributes.get(
            "historical_consumption", {}
        )

        # Append today's data to the historical data
        historical_data[previous_day.strftime("%Y-%m-%d")] = hourly_consumption

        # Update the sensor's state and attributes with historical data
        self._state = total_consumption  # Total consumption for the day
        self._attr_extra_state_attributes = {
            "hourly_consumption": hourly_consumption,  # Current day's data
            "historical_consumption": historical_data,  # All historical data
        }

        _LOGGER.info(
            f"Appended hourly data for {previous_day.strftime('%Y-%m-%d')}: {hourly_consumption}"
        )
