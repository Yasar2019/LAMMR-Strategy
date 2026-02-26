"""Configuration loading utilities."""

import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not Path(config_path).exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_config_value(config: Dict, key: str, default: Any = None) -> Any:
    """Get a config value with optional default."""
    return config.get(key, default)


if __name__ == "__main__":
    config = load_config()
    print(yaml.dump(config, default_flow_style=False))
