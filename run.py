#!python3
import logging

from discord.ext import commands

import common
import plugins

config: dict = common.config["bot"]

client = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description="League of Legends Trivia",
                      pm_help=True)
client.add_cog(plugins.lol.LoLTrivia(client))
client.add_cog(plugins.debug.BotDebug(client))
client.owner_id: str = config["owner_id"]


@client.event
async def on_ready():
    logger.info(f"Logged in. User: {client.user}, ID: {client.user.id}")


@client.event
async def on_command_error(exec: BaseException, ctx: commands.Context):
    if isinstance(exec, (commands.BadArgument, commands.MissingRequiredArgument, commands.CommandOnCooldown)):
        # do these really warrant a traceback?
        return
    logger.error(f'Ignoring exception in command {ctx.command}')
    logger.error("Logging an uncaught exception",
                 exc_info=(type(exec), exec, exec.__traceback__))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', level=logging.INFO)
    logger = logging.getLogger('LoLTrivia')
    logger.info("Logging in...")
    client.run(config["discord_token"])
