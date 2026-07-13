import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class PluginDescriptor(BaseModel):
    name: str
    version: str
    description: str
    entry_point: str
    code: str
    inputs_schema: Dict[str, Any]

class PluginLoader:
    def __init__(self):
        self._registered_plugins: Dict[str, PluginDescriptor] = {}

    def register(self, descriptor: PluginDescriptor) -> None:
        """Registers a custom developer plugin tool."""
        self._registered_plugins[descriptor.name] = descriptor
        logger.info(f"Plugin successfully registered: {descriptor.name} v{descriptor.version}")

    def list_plugins(self) -> List[PluginDescriptor]:
        """Lists registered developer tools."""
        return list(self._registered_plugins.values())

    def get_plugin(self, name: str) -> Optional[PluginDescriptor]:
        return self._registered_plugins.get(name)

plugin_loader = PluginLoader()
