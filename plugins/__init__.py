import importlib

from discord.ext import commands


def load_plugins(bot: commands.Bot, config: dict):
    modules = []
    for plugin in config["plugins"]:
        module = importlib.import_module(f"plugins.{plugin}")
        modules.append(module)
        globals()[plugin] = module

    for module in modules:
        module.init(bot, config)
