from pyforge.plugins.builtin import SyncExecutorPlugin
from pyforge.plugins.registry import PluginRegistry

def create_default_registry(
    discover_external: bool = True,
) -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(SyncExecutorPlugin())

    if discover_external:
        registry.discover()

    return registry


__all__ = [
    "PluginRegistry",
    "create_default_registry",
]
