"""Load the diagram's agents.yaml. A bad file stops the run before any stage."""

from pathlib import Path

import yaml

from cloudeq.plane2_agents.models import STAGE_ORDER, AgentTeam, RoleSpec, StageName

DEFAULT_AGENTS_CONFIG = Path(__file__).with_name("config") / "agents.yaml"


class AgentConfigError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def load_agent_team(path: Path) -> AgentTeam:
    if not path.is_file():
        raise AgentConfigError(f"Agent configuration file was not found: {path}")
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AgentConfigError("Agent configuration is not valid YAML.") from exc
    return parse_agent_team(loaded)


def parse_agent_team(loaded: object) -> AgentTeam:
    if not isinstance(loaded, dict):
        raise AgentConfigError("Agent configuration must be a mapping.")
    version = loaded.get("version")
    roles = loaded.get("roles")
    if version != 1:
        raise AgentConfigError("Agent configuration version must be 1.")
    if not isinstance(roles, list) or not roles:
        raise AgentConfigError("Agent configuration must list the six SDLC roles.")
    parsed: list[RoleSpec] = []
    for item in roles:
        if not isinstance(item, dict):
            raise AgentConfigError("Each role must be a mapping.")
        name = item.get("name")
        goal = item.get("goal")
        label = item.get("diagram_label")
        if not isinstance(name, str) or name not in {stage.value for stage in StageName}:
            raise AgentConfigError(f"Unknown role name: {name!r}.")
        if not isinstance(goal, str) or not goal.strip():
            raise AgentConfigError(f"Role {name} needs a goal.")
        if not isinstance(label, str) or not label.strip():
            raise AgentConfigError(f"Role {name} needs a diagram_label.")
        parsed.append(
            RoleSpec(name=StageName(name), diagram_label=label.strip(), goal=goal.strip())
        )
    names = [role.name for role in parsed]
    if names != list(STAGE_ORDER):
        expected = ", ".join(stage.value for stage in STAGE_ORDER)
        found = ", ".join(role.value for role in names)
        raise AgentConfigError(
            f"Roles must be exactly [{expected}] in that order. Found [{found}]."
        )
    return AgentTeam(version=1, roles=parsed)
