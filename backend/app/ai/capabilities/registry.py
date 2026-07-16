import logging
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class Capability:
    def __init__(self, action: str, description: str = ""):
        self.action = action
        self.description = description

    def __repr__(self):
        return f"Capability({self.action})"


class AgentCapabilities:
    def __init__(self, agent_type: str, capabilities: List[Capability]):
        self.agent_type = agent_type
        self._action_map: Dict[str, Capability] = {c.action: c for c in capabilities}

    def can(self, action: str) -> bool:
        return action in self._action_map

    def get_capability(self, action: str) -> Optional[Capability]:
        return self._action_map.get(action)

    @property
    def actions(self) -> Set[str]:
        return set(self._action_map.keys())

    @property
    def capabilities(self) -> List[Capability]:
        return list(self._action_map.values())


class CapabilityRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentCapabilities] = {}

    def register(self, agent_type: str, capabilities: List[Capability]) -> None:
        self._agents[agent_type] = AgentCapabilities(agent_type, capabilities)
        logger.info(f"Registered capabilities for agent '{agent_type}': {[c.action for c in capabilities]}")

    def find_agents(self, action: str) -> List[str]:
        return [agent for agent, caps in self._agents.items() if caps.can(action)]

    def can_perform(self, agent_type: str, action: str) -> bool:
        agent = self._agents.get(agent_type)
        return agent.can(action) if agent else False

    def get_agent(self, agent_type: str) -> Optional[AgentCapabilities]:
        return self._agents.get(agent_type)

    def all_agents(self) -> Dict[str, AgentCapabilities]:
        return dict(self._agents)

    def all_actions(self) -> Set[str]:
        actions = set()
        for caps in self._agents.values():
            actions.update(caps.actions)
        return actions

    def initialize_defaults(self) -> None:
        self.register("browser", [
            Capability("navigate", "Navigate to a URL"),
            Capability("click", "Click an element by selector"),
            Capability("fill", "Fill an input field"),
            Capability("press", "Press a keyboard key"),
            Capability("wait", "Wait for a duration"),
            Capability("wait_for_selector", "Wait for a CSS selector to appear in DOM"),
            Capability("scrape_text", "Extract visible text from page"),
            Capability("scrape_links", "Extract links from page"),
            Capability("summarize", "Summarize page content using LLM"),
        ])
        self.register("desktop", [
            Capability("click", "Click at screen coordinates"),
            Capability("type", "Type text"),
            Capability("press", "Press a keyboard key"),
        ])
        self.register("file", [
            Capability("find_text", "Search file index for text"),
            Capability("search", "Search files by name"),
            Capability("read", "Read file contents"),
            Capability("write", "Write content to file"),
            Capability("delete", "Delete a file"),
            Capability("list", "List directory contents"),
            Capability("create_directory", "Create a new directory"),
            Capability("move", "Move a file to a new location"),
            Capability("rename", "Rename a file"),
            Capability("copy", "Copy a file to a new location"),
            Capability("move_matching", "Move files matching a keyword or pattern"),
        ])
        self.register("terminal", [
            Capability("run", "Execute a shell command"),
        ])
        self.register("vision", [
            Capability("find_text", "Find text on screen"),
            Capability("capture_elements", "Capture visible UI elements"),
        ])
        logger.info("Default agent capabilities registered")


capability_registry = CapabilityRegistry()
