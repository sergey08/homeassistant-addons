"""Home Assistant integration for the Obsidian MCP server."""

from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError, ConfigEntryNotReady

from .const import DOMAIN
from .http import MCPView
from .runtime import Runtime, Storage


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the endpoint once, independently of entry reloads."""
    hass.http.register_view(MCPView(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry[Runtime]) -> bool:
    """Start the entry with its configured vault."""
    try:
        storage = await hass.async_add_executor_job(
            Storage.check, Path(hass.config.path(DOMAIN)), entry.data
        )
        await hass.async_add_executor_job(storage.prepare, entry.data)
    except (OSError, ValueError) as err:
        raise ConfigEntryError(str(err)) from err

    runtime = Runtime(storage, entry.data)
    try:
        await runtime.start()
    except (OSError, RuntimeError, TimeoutError) as err:
        raise ConfigEntryNotReady("Could not start Obsidian MCP services") from err
    entry.runtime_data = runtime
    hass.data[DOMAIN] = runtime

    async def stop(_event):
        await runtime.stop()

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry[Runtime]) -> bool:
    """Remove access and stop the entry's resources."""
    hass.data.pop(DOMAIN, None)
    await entry.runtime_data.stop()
    return True
