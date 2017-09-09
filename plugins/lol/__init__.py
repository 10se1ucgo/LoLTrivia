from discord.ext import commands

from cassiopeia import riotapi

config: dict = {}


def init(bot: commands.Bot, cfg: dict):
    global config
    config = cfg[__name__]

    riotapi.set_region(config["api_region"])
    riotapi.set_api_key(config["api_key"])

    from .trivia import LoLTrivia
    bot.add_cog(LoLTrivia(bot))
