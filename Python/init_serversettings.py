import logging
from pathlib import Path
import json

from DSPackage.utilities.pipeline_env import get_pipeline_env
from DSPackage.read_data.read import test_readserver
from DSPackage.utilities.logging import log_warning


def init_serversettings(*args):
    logger = logging.getLogger()
    pipeline_env = get_pipeline_env()
    env = pipeline_env[
        "ENV"
    ]  # De branche waarin het script draait. Zie template_python_run_main.yml in DataScience_Resources
    logger.info(f"ENV: {env}")
    # Laad de settings in
    cwd = Path.cwd()
    with open(cwd / "Python" / "server_settings.json", "r", encoding="utf-8") as f:
        server_settings_json = json.load(f)

    if env:
        server_settings = server_settings_json.get(env)
    else:
        server_settings = server_settings_json.get("Ontwikkel")

    readserver_beschikbaar = test_readserver(
        server=server_settings["readserver"], database=server_settings["readdatabase"]
    )

    if not readserver_beschikbaar:
        log_warning(
            f"Readserver {server_settings['readserver']} niet beschikbaar, er wordt overgeschakeld naar readserver {server_settings['fallback_readserver']}"
        )
        server_settings["readserver"] = server_settings["fallback_readserver"]
        server_settings["readdatabase"] = server_settings["fallback_readdatabase"]
        server_settings["readschema"] = server_settings["fallback_readschema"]

    del (
        server_settings["fallback_readserver"],
        server_settings["fallback_readdatabase"],
        server_settings["fallback_readschema"],
    )

    logger.info(f"Server settings: {server_settings}")

    return server_settings
