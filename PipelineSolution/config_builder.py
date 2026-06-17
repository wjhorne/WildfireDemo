"""Config builder: converts parsed queries into DevelopmentSolution configs.

Defaults are inherited from DevelopmentSolution/example_run/INPUTS.md.
"""
from __future__ import annotations

import os
import sys
from typing import Any

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from DevelopmentSolution.simulation import SimulationConfig

from simulation_runner import DEFAULT_PARAMETERS


class ConfigBuilder:
    """Build a SimulationConfig by merging user overrides with defaults."""

    @staticmethod
    def build_config(params: dict[str, Any]) -> SimulationConfig:
        config_dict = dict(DEFAULT_PARAMETERS)
        config_dict.update(params)
        try:
            config = SimulationConfig(**config_dict)
            config.validate()
            return config
        except TypeError as e:
            raise ValueError(f"Invalid configuration keys: {e}")
        except ValueError as e:
            raise ValueError(f"Configuration validation failed: {e}")

    @staticmethod
    def get_defaults() -> dict[str, Any]:
        return dict(DEFAULT_PARAMETERS)


def build_config_from_query(parsed_query: dict[str, Any]) -> SimulationConfig:
    return ConfigBuilder.build_config(parsed_query.get("params", {}))