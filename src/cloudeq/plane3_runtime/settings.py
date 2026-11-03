"""Plane 3 settings. Secrets are not read here."""

import re
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_MEMORY = re.compile(r"^[1-9]\d{0,5}[bkmgBKMG]?$")
_CPUS = re.compile(r"^[1-9]\d{0,2}(\.\d{1,2})?$")
_IMAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}$")
_USER = re.compile(r"^[0-9]{1,6}:[0-9]{1,6}$")


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    cloudeq_runtime_workspace_root: str = "~/.cloudeq/runtime_workspaces"
    cloudeq_runtime_network: Literal["none"] = "none"
    cloudeq_runtime_timeout_seconds: float = Field(default=120, gt=0, le=600)
    cloudeq_runtime_memory: str = "512m"
    cloudeq_runtime_cpus: str = "1"
    cloudeq_runtime_pids_limit: int = Field(default=64, gt=0, le=256)
    cloudeq_runtime_allow_git_commit: bool = False
    cloudeq_runtime_allow_git_push: bool = False
    cloudeq_runtime_allow_host_execution: bool = False
    cloudeq_runtime_image: str = "cloudeq-runtime:py3.12-pytest9.2.0"
    cloudeq_runtime_user: str = "65534:65534"
    cloudeq_runtime_output_limit: int = Field(default=8192, gt=0, le=65536)

    def validate_policy(self) -> None:
        if self.cloudeq_runtime_allow_host_execution:
            raise ValueError("Host execution is not allowed.")
        if self.cloudeq_runtime_allow_git_push:
            raise ValueError("Git push is not a runtime operation.")
        if self.cloudeq_runtime_network != "none":
            raise ValueError("Container network must stay disabled.")
        if _MEMORY.fullmatch(self.cloudeq_runtime_memory) is None:
            raise ValueError("Container memory limit is invalid.")
        if _CPUS.fullmatch(self.cloudeq_runtime_cpus) is None:
            raise ValueError("Container CPU limit is invalid.")
        if _IMAGE.fullmatch(self.cloudeq_runtime_image) is None:
            raise ValueError("Container image reference is invalid.")
        if _USER.fullmatch(self.cloudeq_runtime_user) is None:
            raise ValueError("Container user must be a non-root numeric uid:gid.")
        uid = int(self.cloudeq_runtime_user.split(":", 1)[0])
        if uid == 0:
            raise ValueError("Container user must not be root.")
