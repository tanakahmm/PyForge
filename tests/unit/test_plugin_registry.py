import pytest
from pyforge.engine.executor import Executor
from pyforge.exceptions import (
    PluginNotFoundError,
    PluginRegistrationError,
)
from pyforge.plugins import create_default_registry
from pyforge.plugins.base import ExecutorPlugin
from pyforge.plugins.registry import PluginRegistry
from pyforge.engine.sync_executor import SyncExecutor


class FakeExecutorPlugin(ExecutorPlugin):
    @property
    def name(self) -> str:
        return "fake"

    def create_executor(self) -> Executor:
        return SyncExecutor()


def test_default_registry_contains_sync_plugin():
    registry = create_default_registry(discover_external=False)

    assert registry.list_plugins() == ["sync"]


def test_registry_creates_sync_executor():
    registry = create_default_registry(discover_external=False)

    executor = registry.create_executor("sync")

    assert isinstance(executor, SyncExecutor)


def test_register_custom_plugin():
    registry = PluginRegistry()
    registry.register(FakeExecutorPlugin())

    assert registry.list_plugins() == ["fake"]
    assert isinstance(
        registry.create_executor("fake"),
        SyncExecutor,
    )


def test_duplicate_plugin_name_is_rejected():
    registry = PluginRegistry()
    registry.register(FakeExecutorPlugin())

    with pytest.raises(PluginRegistrationError):
        registry.register(FakeExecutorPlugin())


def test_unknown_plugin_raises_error():
    registry = PluginRegistry()

    with pytest.raises(PluginNotFoundError):
        registry.create_executor("does-not-exist")


def test_non_plugin_object_is_rejected():
    registry = PluginRegistry()

    with pytest.raises(PluginRegistrationError):
        registry.register(object())
