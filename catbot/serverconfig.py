import threading
import copy
import json
import os


class CatbotConfig:
    """
    JSON configuration
    object contains a list of servers, each server contains a config object
    each config object should contain:
        server_prefix
        macros
    """
    CONFIG_PATH = "config.json"

    config_lock = threading.Semaphore(1)
    servers = {}
    initialized = False

    @staticmethod
    def _save_config_unsafe():
        with open(CatbotConfig.CONFIG_PATH, "w") as cfgfile:
            json.dump(CatbotConfig.servers, cfgfile)
            print("saved", CatbotConfig.servers)

    @staticmethod
    def reload_config():
        CatbotConfig.initialized = False
        CatbotConfig._load_config()

    @staticmethod
    def _load_config():
        CatbotConfig.config_lock.acquire()
        # second init check
        if CatbotConfig.initialized:
            return
        try:
            if os.path.exists(CatbotConfig.CONFIG_PATH):
                with open(CatbotConfig.CONFIG_PATH, "r") as cfgfile:
                    CatbotConfig.servers = json.load(cfgfile)
            else:
                with open(CatbotConfig.CONFIG_PATH, "w") as cfgfile:
                    cfgfile.write("{}")
        finally:
            CatbotConfig.initialized = True
            CatbotConfig.config_lock.release()
        print("loaded", CatbotConfig.servers)

    @staticmethod
    def get_config(server):
        """Returns a copy of the config, use commit_config to save changes"""
        if not CatbotConfig.initialized:
            CatbotConfig._load_config()
        config = CatbotConfig.servers.get(server, {})
        return copy.deepcopy(config)

    @staticmethod
    def commit_config(server, config):
        if not CatbotConfig.initialized:
            CatbotConfig._load_config()
        CatbotConfig.config_lock.acquire()
        try:
            CatbotConfig.servers[server] = config
            CatbotConfig._save_config_unsafe()
        finally:
            CatbotConfig.config_lock.release()
