import yaml
import os

with open("/app/config/settings.yaml", "r") as f:
    settings = yaml.safe_load(f)

settings["auth"] = {
    "api_key": os.environ.get("API_KEY")
}

settings["search"]["tavily_api_key"] = os.environ.get("TAVILY_API_KEY")