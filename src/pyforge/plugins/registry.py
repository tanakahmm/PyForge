
from importlib.metadata import entry_points

from pyforge.engine.executor import Executor
from pyforge.exceptions import (
    PluginNotFoundError,
    PluginRegistrationError,
)
from pyforge.plugins.base import ExecutorPlugin


class PluginRegistry:
    """Register, discover and instantiate executor plugins."""

    ENTRY_POINT_GROUP = "pyforge.executors"

    def __init__(self) -> None:
        self._plugins: dict[str, ExecutorPlugin] = {}

    def register(self, plugin: ExecutorPlugin) -> None:
        if not isinstance(plugin, ExecutorPlugin):
            raise PluginRegistrationError(
                "Plugin must inherit from ExecutorPlugin."
            )

        name = plugin.name

        if not isinstance(name, str) or not name.strip():
            raise PluginRegistrationError(
                "Plugin name must be a non-empty string."
            )

        if name in self._plugins:
            raise PluginRegistrationError(
                f"Plugin '{name}' is already registered."
            )

        self._plugins[name] = plugin

    def get_plugin(self, name: str) -> ExecutorPlugin:
        try:
            return self._plugins[name]
        except KeyError:
            raise PluginNotFoundError(
                f"Plugin '{name}' was not found."
            ) from None

    def create_executor(self, name: str) -> Executor:
        plugin = self.get_plugin(name)
        executor = plugin.create_executor()

        if not isinstance(executor, Executor):
            raise PluginRegistrationError(
                f"Plugin '{name}' did not create a valid Executor."
            )

        return executor

    def list_plugins(self) -> list[str]:
        return sorted(self._plugins)

    def discover(self) -> None:
        """Load plugins advertised by installed Python packages."""

        for entry_point in entry_points(
            group=self.ENTRY_POINT_GROUP
        ):
            plugin_class = entry_point.load()
            plugin = plugin_class()
            self.register(plugin)
