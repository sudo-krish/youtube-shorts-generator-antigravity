import os
import json

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
)

DEFAULT_CONFIG = {
    "models": {
        "observer": "deepseek-v4-flash",
        "scriptwriter": "deepseek-v4-flash",
        "director": "deepseek-v4-flash",
        "editor": "deepseek-v4-pro",
        "specialist": "deepseek-v4-pro",
        "builder": "deepseek-v4-flash",
    }
}


def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
                # Ensure all default keys exist
                config = DEFAULT_CONFIG.copy()
                if "models" in data:
                    config["models"].update(data["models"])
                return config
        except Exception:
            return DEFAULT_CONFIG
    return DEFAULT_CONFIG


def set_config(new_config):
    config = get_config()
    if "models" in new_config:
        config["models"].update(new_config["models"])

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    return config
