# Based on Rapptz's RoboDanny's repl cog
import contextlib
import inspect
import logging
import re
import sys
import textwrap
import traceback
from io import StringIO
from typing import *
from typing import Pattern

import discord
from discord.ext import commands

# i took this from somewhere and i cant remember where
md: Pattern = re.compile(r"^(([ \t]*`{3,4})([^\n]*)(?P<code>[\s\S]+?)(^[ \t]*\2))", re.MULTILINE)
logger = logging.getLogger(__name__)


class BotDebug(object):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.last_eval = None

    @commands.command(hidden=True)
    async def exec(self, ctx: commands.Context, *, cmd: str):
        result, stdout, stderr = await self.run(ctx, cmd, use_exec=True)
        await self.send_output(ctx, result, stdout, stderr)

    @commands.command(hidden=True)
    async def eval(self, ctx: commands.Context, *, cmd: str):
        scope = {"_": self.last_eval, "last": self.last_eval}
        result, stdout, stderr = await self.run(ctx, cmd, use_exec=False, extra_scope=scope)
        self.last_eval = result
        await self.send_output(ctx, result, stdout, stderr)

    async def send_output(self, ctx: commands.Context, result: str, stdout: str, stderr: str):
        print(result, stdout, stderr)
        if result is not None:
            await ctx.send(f"Result: `{result}`")
        if stdout:
            logger.info(f"exec stdout: \n{stdout}")
            await ctx.send("stdout:")
            await self.send_split(ctx, stdout)
        if stderr:
            logger.error(f"exec stderr: \n{stderr}")
            await ctx.send("stderr:")
            await self.send_split(ctx, stderr)

    async def run(self, ctx: commands.Context, cmd: str, use_exec: bool, extra_scope: dict=None) -> Tuple[Any, str, str]:
        if not self.client.is_owner(ctx.author):
            return None, "", ""

        # note: exec/eval inserts __builtins__ if a custom version is not defined (or set to {} or whatever)
        scope: Dict[str, Any] = {'bot': self.client, 'ctx': ctx, 'discord': discord}
        if extra_scope:
            scope.update(extra_scope)

        match: Match = md.match(cmd)
        code: str = match.group("code").strip() if match else cmd.strip('` \n')
        logger.info(f"Executing code '{code}'")

        result = None
        with std_redirect() as (stdout, stderr):
            try:
                if use_exec:
                    # wrap in async function to run in loop and allow await calls
                    func = f"async def run():\n{textwrap.indent(code, '    ')}"
                    exec(func, scope)
                    result = await scope['run']()
                else:
                    result = eval(code, scope)
                    # eval doesn't allow `await`
                    if inspect.isawaitable(result):
                        result = await result
            except (SystemExit, KeyboardInterrupt):
                raise
            except Exception:
                await self.on_error(ctx)
            else:
                await ctx.message.add_reaction('✅')
        return result, stdout.getvalue(), stderr.getvalue()

    async def on_error(self, ctx: commands.Context):
        # prepend a "- " to each line and use ```diff``` syntax highlighting to color the error message red.
        # also strip lines 2 and 3 of the traceback which includes full path to the file, irrelevant for repl code.
        # yes i know error[:1] is basically error[0] but i want it to stay as a list
        logger.exception("Error in exec code")

        error = traceback.format_exc().splitlines()
        error = textwrap.indent('\n'.join(error[:1] + error[3:]), '- ', lambda x: True)
        await ctx.send("Traceback:")
        await self.send_split(ctx, error, prefix="```diff\n")

    async def send_split(self, ctx: commands.Context, text: str, *, prefix="```\n", postfix="\n```"):
        max_len = 2000 - (len(prefix) + len(postfix))
        text: List[str] = [text[x:x+max_len] for x in range(0, len(text), max_len)]
        print(text)
        for message in text:
            await ctx.send(f"{prefix}{message}{postfix}")


@contextlib.contextmanager
def std_redirect():
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = StringIO()
    sys.stderr = StringIO()
    yield sys.stdout, sys.stderr
    sys.stdout = stdout
    sys.stderr = stderr


def init(bot: commands.Bot, cfg: dict):
    bot.add_cog(BotDebug(bot))

