DOMAIN = "besmart"

async def async_setup(hass, config):
    return True
async def async_setup_entry(hass, entry):
    hass.config_entries.async_setup_platforms(entry, ["climate"])
    return True

