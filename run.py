#!python3
import json
import logging

from discord.ext import commands

import plugins

with open("config.json", "r") as f:
    config: dict = json.load(f)

client = commands.Bot(command_prefix=commands.when_mentioned_or('!'), description="League of Legends Trivia",
                      pm_help=True, owner_id=config["bot"]["owner_id"] or None)

plugins.load_plugins(client, config)


@client.event
async def on_ready():
    logger.info(f"Logged in. User: {client.user}, ID: {client.user.id}")


@client.event
async def on_command_error(ctx: commands.Context, e: BaseException):
    if isinstance(e, (commands.BadArgument, commands.MissingRequiredArgument, commands.CommandOnCooldown)):
        # do these really warrant a traceback?
        return
    logger.error(f'Ignoring exception in command {ctx.command}')
    logger.error("Logging an uncaught exception",
                 exc_info=(type(e), e, e.__traceback__))


if __name__ == "__main__":
    logging.basicConfig(format='%(asctime)s::%(name)s::%(levelname)s::%(message)s', level=logging.INFO)
    logger = logging.getLogger('LoLTrivia')
    logger.info("Logging in...")
    client.run(config["bot"]["discord_token"])
