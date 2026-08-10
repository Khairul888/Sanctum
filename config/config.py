import yaml
import os

with open("/app/config/settings.yaml", "r") as f:
    settings = yaml.safe_load(f)