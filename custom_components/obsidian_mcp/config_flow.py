"""Configure storage, remote access and provisioning from Home Assistant."""

from functools import partial
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .const import DOMAIN
from .couchdb_check import CouchCheckError, check_couchdb
from .runtime import Storage
from .settings_import import SettingsImportError, import_settings_json
from .tunnel_key import TunnelKeyError, store_runtime_key

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
MULTILINE = TextSelector(TextSelectorConfig(multiline=True))


class ObsidianConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure a single Obsidian MCP instance."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self._configure("user", {}, user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._configure(
            "reconfigure", self._get_reconfigure_entry().data, user_input
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return ObsidianOptionsFlow()

    async def _configure(self, step, current, user_input):
        errors = {}
        message = ""
        values = current if user_input is None else user_input
        key = current.get("remote_mcp_api_key", "")
        if user_input is not None:
            submitted = dict(user_input)
            for field in ("vault_path", "livesync_shared_vault_path", "tunnel_id"):
                submitted[field] = submitted.get(field, "").strip()
            submitted["remote_mcp_api_key"] = (
                submitted.get("remote_mcp_api_key", "").strip() or key
                if submitted.get("enable_remote_mcp")
                else ""
            )
            try:
                await self.hass.async_add_executor_job(
                    Storage.check, Path(self.hass.config.path(DOMAIN)), submitted
                )
            except (OSError, ValueError) as err:
                errors["base"] = "invalid_configuration"
                message = str(err) if isinstance(err, ValueError) else type(err).__name__
            else:
                if step == "reconfigure":
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data=submitted
                    )
                return self.async_create_entry(title="Obsidian MCP", data=submitted)
        schema = vol.Schema({
            vol.Required("storage_mode", default=values.get("storage_mode", "livesync")):
                vol.In(["local", "livesync"]),
            vol.Optional("vault_path", description={"suggested_value": values.get("vault_path", "")}): str,
            vol.Optional("livesync_shared_vault_path", description={
                "suggested_value": values.get("livesync_shared_vault_path", "")
            }): str,
            vol.Required("enable_livesync", default=values.get("enable_livesync", False)): bool,
            vol.Required("livesync_interval", default=values.get("livesync_interval", 60)):
                vol.All(vol.Coerce(int), vol.Range(min=30, max=3600)),
            vol.Required("enable_tunnel", default=values.get("enable_tunnel", False)): bool,
            vol.Optional("tunnel_id", description={"suggested_value": values.get("tunnel_id", "")}): str,
            vol.Required("enable_remote_mcp", default=values.get("enable_remote_mcp", False)): bool,
            vol.Optional("remote_mcp_api_key"): PASSWORD,
        })
        return self.async_show_form(
            step_id=step,
            data_schema=schema,
            errors=errors,
            description_placeholders={"detail": message if errors else ""},
        )


class ObsidianOptionsFlow(OptionsFlow):
    """Provision existing files and check CouchDB without enabling synchronization."""

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(
            step_id="init",
            menu_options=["status", "import_livesync", "save_tunnel_key", "check_couchdb"],
        )

    async def async_step_status(self, user_input=None):
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime and runtime.url:
            status = {
                key: ("disabled" if proc is None else
                      "running" if proc.returncode is None else f"exit {proc.returncode}")
                for key, proc in (
                    ("livesync", runtime.processes.get("LiveSync")),
                    ("tunnel", runtime.processes.get("OpenAI tunnel")),
                )
            }
            status["vault"] = str(runtime.storage.vault)
        else:
            status = dict.fromkeys(("vault", "livesync", "tunnel"), "—")
        return self.async_abort(reason="runtime_status", description_placeholders=status)

    async def async_step_import_livesync(self, user_input=None):
        return await self._provision("import_livesync", MULTILINE, user_input)

    async def async_step_save_tunnel_key(self, user_input=None):
        return await self._provision("save_tunnel_key", PASSWORD, user_input)

    async def async_step_check_couchdb(self, user_input=None):
        return await self._provision("check_couchdb", None, user_input)

    async def _provision(self, step, selector, user_input):
        errors = {}
        message = ""
        if user_input is not None:
            base = Path(self.hass.config.path(DOMAIN))
            if step == "import_livesync":
                job = partial(import_settings_json, user_input["value"].encode(), base)
            elif step == "save_tunnel_key":
                job = partial(store_runtime_key, user_input["value"], base)
            else:
                job = partial(check_couchdb, base / "settings/livesync-operativo.json")
            try:
                message = await self.hass.async_add_executor_job(job)
            except (SettingsImportError, TunnelKeyError, CouchCheckError) as err:
                message = str(err)
                errors["base"] = "provisioning_failed"
            except OSError:
                message = "File unavailable"
                errors["base"] = "provisioning_failed"
            else:
                return self.async_abort(reason="provisioning_done", description_placeholders={"detail": message})
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema({vol.Required("value"): selector} if selector else {}),
            errors=errors,
            description_placeholders={"detail": message},
        )
