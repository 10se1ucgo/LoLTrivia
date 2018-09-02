from discord.ext import commands

import cassiopeia as riotapi

config: dict = {}


def init(bot: commands.Bot, cfg: dict):
    config.update(cfg[__name__])

    riotapi.set_default_region(config["api_region"])
    riotapi.set_riot_api_key(config["api_key"])

    from .trivia import LoLTrivia
    bot.add_cog(LoLTrivia(bot))
