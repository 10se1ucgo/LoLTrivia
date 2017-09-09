# Based on Rapptz's RoboDanny's repl cog
import contextlib
import inspect
import logging
import re
import sys
import textwrap
import traceback
from io import StringIO
from typing import Pattern, Match, Any, Dict, Tuple

from discord.ext import commands

# i took this from somewhere and i cant remember where
md: Pattern = re.compile(r"^(([ \t]*`{3,4})([^\n]*)(?P<code>[\s\S]+?)(^[ \t]*\2))", re.MULTILINE)
logger = logging.getLogger(__name__)


class BotDebug(object):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.last_eval = None

    @commands.command(pass_context=True, hidden=True)
    async def exec(self, ctx: commands.Context, *, cmd: str):
        result, stdout, stderr = await self.run(ctx, cmd, use_exec=True)
        await self.say_output(result, stdout, stderr)

    @commands.command(pass_context=True, hidden=True)
    async def eval(self, ctx: commands.Context, *, cmd: str):
        scope = {"_": self.last_eval, "last": self.last_eval}
        result, stdout, stderr = await self.run(ctx, cmd, use_exec=False, extra_scope=scope)
        self.last_eval = result
        await self.say_output(result, stdout, stderr)

    async def say_output(self, result, stdout, stderr):
        if result is not None:
            await self.client.say(f"Result: `{result}`")
        if stdout:
            logger.info(f"exec stdout: \n{stdout}")
            await self.client.say(f"stdout: ```\n{stdout}\n```")
        if stderr:
            logger.error(f"exec stderr: \n{stderr}")
            await self.client.say(f"stderr: ```fix\n{stderr}\n```")

    async def run(self, ctx: commands.Context, cmd: str, use_exec: bool, extra_scope: dict=None) -> Tuple[Any, str, str]:
        if ctx.message.author.id != self.client.owner_id:
            return None, "", ""

        # note: exec/eval inserts __builtins__ if a custom version is not defined (or set to {} or whatever)
        scope: Dict[str, Any] = {'bot': self.client, 'ctx': ctx}
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
                await self.on_error()
            else:
                await self.client.add_reaction(ctx.message, '✅')
        return result, stdout.getvalue(), stderr.getvalue()

    async def on_error(self):
        # prepend a "- " to each line and use ```diff``` syntax highlighting to color the error message red.
        # also strip lines 2 and 3 of the traceback which includes full path to the file, irrelevant for repl code.
        # yes i know error[:1] is basically error[0] but i want it to stay as a list
        logger.exception("Error in exec code")

        error = traceback.format_exc().splitlines()
        error = textwrap.indent('\n'.join(error[:1] + error[3:]), '- ', lambda x: True)
        await self.client.say(f"Traceback: ```diff\n{error}\n```")


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

