
class PyForgeError(Exception):
    """Base exception for PyForge."""


class JobNotFoundError(PyForgeError):
    """Raised when a requested job does not exist."""


class JobResultNotFoundError(PyForgeError):
    """Raised when a job result does not exist."""


class StorageError(PyForgeError):
    """Raised when a storage operation fails."""

class PluginError(PyForgeError):
    """Base exception for plugin-related failures."""


class PluginNotFoundError(PluginError):
    """Raised when a plugin name is not registered."""


class PluginRegistrationError(PluginError):
    """Raised when a plugin cannot be registered."""