import asyncio
import operator
import textwrap
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import *

import discord
from cassiopeia import riotapi
from cassiopeia.type.core.staticdata import *
from discord.ext import commands

from plugins.lol import db, questions, util, config


class LoLTrivia(object):
    def __init__(self, client: commands.Bot):
        self.client = client
        self.questions: DefaultDict[discord.Channel, Dict[questions.Question, asyncio.Task]] = defaultdict(dict)
        # self.timers: Dict[discord.Channel, float] = defaultdict(float)
        self.user_db = db.TriviaDB("data/users.db")

        # add the force_index acceptable values to the !trivia force command.
        force_help = ['\n']
        for x, func in enumerate(questions._questions):
            force_help.append(f"{x}. {func.__name__}")
        self.force.help += '\n'.join(force_help)
        self.trivia.help = self.trivia.help.format(max=config["trivia"]["max_games"])

    @commands.cooldown(rate=1, per=config["trivia"]["cd"], type=commands.BucketType.server)
    @commands.group(pass_context=True, invoke_without_command=True)
    async def trivia(self, ctx: commands.Context, num: int=1):
        """Starts a game of LoL Trivia.
        
        [num] specifies the number of games to play. Max {max}. Only staff can play more than 1 game.
        """
        # if time.time() - self.timers[ctx.message.channel] < config["trivia_cd"]: return
        # self.timers[ctx.message.channel] = time.time()
        if self.questions[ctx.message.channel]: return

        if discord.utils.get(ctx.message.channel.server.me.roles, name="DisableTrivia") is not None: return

        if not ctx.message.author.permissions_in(ctx.message.channel).manage_messages:
            num = 1
        return await self.start_trivia(ctx, num)

    @trivia.command(pass_context=True)
    @commands.has_permissions(manage_messages=True)
    async def force(self, ctx: commands.Context, num: int=1, force_index: int=None):
        """Force starts a game of trivia, regardless of cooldown.
        If [force_index] is specified, that specific question type will be played.
        """
        # if not ctx.message.author.permissions_in(ctx.message.channel).manage_messages: return
        return await self.start_trivia(ctx, num, force_index)

    @trivia.command(pass_context=True)
    @commands.has_permissions(manage_messages=True)
    async def cancel(self, ctx: commands.Context):
        """Force starts a game of trivia, regardless of cooldown.
        If [force_index] is specified, that specific question type will be played.
        """
        # if not ctx.message.author.permissions_in(ctx.message.channel).manage_messages: return
        self.questions[ctx.message.channel].pop(running, None)

        for q, task in list(self.questions[ctx.message.channel].items()):
            self.questions[ctx.message.channel].pop(q, None)
            if not q: continue
            task.cancel()

    @trivia.command(pass_context=True)
    async def info(self, ctx: commands.Context, arg1: str, arg2: str=""):
        """Returns info on a champ/item/skin/summ/rune/mastery (best guess).
        """
        # messy and often slow but im too lazy to fix
        if self.questions[ctx.message.channel]:
            return

        start: float = time.time()
        embed: discord.Embed = None

        items: List[Tuple[Any, int]] = [
            util.get_champion_by_name(arg1),
            util.get_item(arg1),
            util.get_skin_by_name(arg1),
            util.get_by_name(arg1, riotapi.get_summoner_spells()),
            util.get_by_name(arg1, riotapi.get_runes()),
            util.get_by_name(arg1, riotapi.get_masteries())
        ]

        info_item, score = max(items, key=operator.itemgetter(1))

        if isinstance(info_item, Champion):
            embed = self.champ_info(info_item, arg2)
        elif isinstance(info_item, Item):
            embed = self.item_info(info_item)
        elif isinstance(info_item, util.SkinInfo):
            embed = self.skin_info(info_item, arg2)
        elif isinstance(info_item, SummonerSpell):
            embed = self.summ_info(info_item)
        elif isinstance(info_item, Rune):
            embed = self.rune_info(info_item)
        elif isinstance(info_item, Mastery):
            embed = self.mastery_info(info_item)

        if not embed:
            return await self.client.say("No match found.")

        footer = f"Time elapsed: {(time.time() - start) * 1000:.0f} ms/Match Score: {score}"
        await self.client.say(embed=embed.set_footer(text=footer))

    @trivia.command(pass_context=True)
    async def champ(self, ctx: commands.Context, champ_name: str, spell_key: str= ""):
        """Returns info on a champion (title, passive, spells).
        
        Additionally, [spell_name] can be specified as one of "Q", "W", "E", "R", "P",
            returning specific info about that spell.
        """
        if self.questions[ctx.message.channel]:
            return

        champ, score = util.get_champion_by_name(champ_name)
        if not champ:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.champ_info(champ, spell_key).set_footer(text=f"Match Score: {score}"))

    @trivia.command(pass_context=True)
    async def item(self, ctx: commands.Context, *, item_name_or_id: str):
        """Returns info on a item (name, stats, gold values, etc).
        """
        if self.questions[ctx.message.channel]:
            return

        item, score = util.get_item(item_name_or_id)
        if not item:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.item_info(item).set_footer(text=f"Match Score: {score}"))

    @trivia.command(pass_context=True)
    async def skin(self, ctx: commands.Context, skin_name: str, type: str=""):
        """Returns info on a skin (name, price, release date, splash art)

        Can specify [type] as "loading" to get loading screen slice.
        """
        if self.questions[ctx.message.channel]:
            return

        skin, score = util.get_skin_by_name(skin_name)
        if not skin:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.skin_info(skin, type).set_footer(text=f"Match Score: {score}"))

    @trivia.command(pass_context=True)
    async def summ(self, ctx: commands.Context, *, summ_name: str):
        """Returns info on a summoner spell (name, cooldown, required level, tooltip).
        """
        if self.questions[ctx.message.channel]:
            return

        summ, score = util.get_by_name(summ_name, riotapi.get_summoner_spells())
        if not summ:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.summ_info(summ).set_footer(text=f"Match Score: {score}"))

    @trivia.command(pass_context=True)
    async def rune(self, ctx: commands.Context, *, rune_name: str):
        """Returns info on a rune (name, tier, description).
        """
        if self.questions[ctx.message.channel]:
            return

        rune, score = util.get_by_name(rune_name, riotapi.get_runes())
        if not rune:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.rune_info(rune).set_footer(text=f"Match Score: {score}"))

    @trivia.command(pass_context=True)
    async def mastery(self, ctx: commands.Context, *, mastery_name: str):
        """Returns info on a mastery (name, tree, description).
        """
        if self.questions[ctx.message.channel]:
            return

        mastery, score = util.get_by_name(mastery_name, riotapi.get_masteries())
        if not mastery:
            return await self.client.say("No match found.")
        await self.client.say(embed=self.mastery_info(mastery).set_footer(text=f"Match Score: {score}"))

    def champ_info(self, champ: Champion, spell_key: str):
        if spell_key.lower() == "p":
            return self.passive_info(champ)
        elif spell_key.lower() in ('q', 'w', 'e', 'r'):
            return self.spell_info(champ, spell_key=spell_key)

        passive: Passive = champ.passive

        embed = discord.Embed(title=f"{champ.name}, {champ.title}", description='/'.join(champ.tags),
                              url=f"http://leagueoflegends.wikia.com/wiki/{champ.name.replace(' ', '_')}",
                              type="rich", color=discord.Color.blue())
        embed.set_thumbnail(url=util.get_image_link(champ.image))

        embed.add_field(name=f"Passive - {passive.name}",
                        value=textwrap.shorten(passive.sanitized_description, 125, placeholder="..."), inline=False)
        for x, spell in enumerate(champ.spells):
            embed.add_field(name=f"{'QWER'[x]} - {spell.name}",
                            value=textwrap.shorten(spell.sanitized_description, 125, placeholder="..."))

        return embed

    def spell_info(self, champ: Champion, spell_key: str):
        spell: Spell = champ.spells["qwer".index(spell_key.lower())]

        champ_name_link = champ.name.replace(' ', '_')
        url_anchored = f"{champ_name_link}#{spell.name.replace(' ', '_')}"
        embed = discord.Embed(title=f"{spell.name} ({spell_key.upper()})",
                              description=util.parse_tooltip(spell, spell.resource),
                              url=f"http://leagueoflegends.wikia.com/wiki/{url_anchored}",
                              type="rich", color=discord.Color.blue())
        embed.set_author(name=f"{champ.name}", icon_url=util.get_image_link(champ.image),
                         url=f"http://leagueoflegends.wikia.com/wiki/{champ_name_link}")
        embed.set_thumbnail(url=util.get_image_link(spell.image))

        embed.add_field(name="Cooldown", value=spell.cooldown_burn)
        embed.add_field(name="Range", value=spell.range_burn)
        embed.add_field(name="Tooltip", value=util.parse_tooltip(spell, util.SANITIZER.handle(spell.tooltip)),
                        inline=False)
        return embed

    def passive_info(self, champ: Champion):
        passive: Passive = champ.passive

        champ_name_link = champ.name.replace(' ', '_')
        url_anchored = f"{champ_name_link}#{passive.name.replace(' ', '_')}"
        embed = discord.Embed(title=f"{passive.name} (Passive)",
                              description=util.SANITIZER.handle(passive.description),
                              url=f"http://leagueoflegends.wikia.com/wiki/{url_anchored}",
                              type="rich", color=discord.Color.blue())
        embed.set_author(name=f"{champ.name}", icon_url=util.get_image_link(champ.image),
                         url=f"http://leagueoflegends.wikia.com/wiki/{champ_name_link}")
        embed.set_thumbnail(url=util.get_image_link(passive.image))

        return embed

    def skin_info(self, info: util.SkinInfo, type: str=None):
        champ_name_link = info.champ.name.replace(' ', '_')
        skin_name = info.skin.name if info.skin.name != "default" else f"Classic {info.champ.name}"
        embed = discord.Embed(title=f"{skin_name}", type="rich", color=discord.Color.blue(),
                              url=f"http://leagueoflegends.wikia.com/wiki/{champ_name_link}/Skins")
        embed.set_author(name=f"{info.champ.name}", icon_url=util.get_image_link(info.champ.image),
                         url=f"http://leagueoflegends.wikia.com/wiki/{champ_name_link}")
        embed.add_field(name="Price", value="Free/Limited Edition"
        if info.price and info.price.isdigit() and int(info.price) <= 0
        else f"{info.price} RP")
        embed.add_field(name="Release Date", value=info.date)
        embed.set_image(url=info.skin.loading if type and type.lower() == "loading" else info.skin.splash)

        return embed

    def item_info(self, item: Item):
        embed = discord.Embed(title=f"{item.name}",
                              description=util.SANITIZER.handle(item.description),
                              url=f"http://leagueoflegends.wikia.com/wiki/{item.name.replace(' ', '_')}",
                              type="rich", color=discord.Color.blue())
        embed.set_thumbnail(url=util.get_image_link(item.image))

        if item.gold.total != 0:
            embed.add_field(name="Gold (Buy)", value=f"{item.gold.total}g")
            embed.add_field(name="Gold (Sell)", value=f"{item.gold.sell}g")
        if item.gold.total != item.gold.base:
            embed.add_field(name="Gold (Recipe)", value=f"{item.gold.base}g")
        embed.add_field(name="Purchasable?", value="Yes" if item.gold.purchasable else "No")
        if item.components:
            embed.add_field(name="Builds From", value=', '.join(x.name for x in item.components))
        if item.component_of:
            embed.add_field(name="Builds Into", value=', '.join(x.name for x in item.component_of))
        return embed

    def summ_info(self, summ: SummonerSpell):
        embed = discord.Embed(title=summ.name, description=f"Available at summoner level {summ.summoner_level}",
                              url=f"http://leagueoflegends.wikia.com/wiki/{summ.name.replace(' ', '_')}",
                              type="rich", color=discord.Color.blue())
        embed.set_thumbnail(url=util.get_image_link(summ.image))
        embed.add_field(name="Cooldown", value=summ.cooldown_burn)
        embed.add_field(name="Range", value=summ.range_burn)
        embed.add_field(name="Tooltip", value=util.parse_tooltip(summ, util.SANITIZER.handle(summ.tooltip)),
                        inline=False)
        return embed

    def rune_info(self, rune: Rune):
        embed = discord.Embed(title=rune.name, description=f"Tier {rune.meta_data.tier}",
                              type="rich", color=discord.Color.blue())
        embed.set_thumbnail(url=util.get_image_link(rune.image))
        embed.add_field(name="Description", value=util.SANITIZER.handle(rune.description),
                        inline=False)
        return embed

    def mastery_info(self, mastery: Mastery):
        embed = discord.Embed(title=mastery.name, description=f"{mastery.tree.value} Tree",
                              url=f"http://leagueoflegends.wikia.com/wiki/{mastery.name.replace(' ', '_')}",
                              type="rich", color=discord.Color.blue())
        embed.set_thumbnail(url=util.get_image_link(mastery.image))
        embed.add_field(name="Description (at max rank)", value=util.SANITIZER.handle(mastery.descriptions[-1]),
                        inline=False)
        embed.add_field(name="Max Rank", value=str(mastery.max_rank), inline=False)
        return embed

    @trivia.command(pass_context=True)
    async def score(self, ctx: commands.Context, *, user: discord.Member=None):
        """Returns the score of [user]. Defaults to you.
        """
        points = self.user_db.get_score(ctx.message.author.id if user is None else user.id) or 0
        if user is None:
            await self.client.reply(f"your score is {points} points.")
        else:
            await self.client.say(f"{user.mention}'s score is {points} points")

    @trivia.command(pass_context=True)
    async def top(self, ctx: commands.Context):
        """Returns the top 10 scores
        """
        embed = discord.Embed(title=f"LoL Trivia Scoreboard", description="Top 10 LoL Trivia players\n\n",
                              type="rich", color=discord.Color.blue())
        for x, (id, score) in enumerate(self.user_db.get_top(), start=1):
            user = ctx.message.server.get_member(id)
            name = f"{user.name}#{user.discriminator}" if user else id
            embed.add_field(name=f"{x}. {name}", value=f"{score} points")
        await self.client.say(embed=embed)

    async def start_trivia(self, ctx: commands.Context, num: int=1, force_index: int=None):
        num = max(1, min(num, config["trivia"]["max_games"]))

        await self.client.say(f"{ctx.message.author.mention} started a game of LoL Trivia! Get ready!")

        with self.lock_questions(ctx.message.channel):
            for x in range(num):
                if not self.questions[ctx.message.channel].get(running, None):
                    break
                await asyncio.sleep(2)
                q: questions.Question = questions.get_random_question(force_index)
                await q.say(self.client, ctx.message.channel)
                task = asyncio.ensure_future(self.question_helper(q, ctx.message.channel))
                self.questions[ctx.message.channel][q] = task
                await task

        await self.client.say(f"You can start a new round in {config['trivia']['cd']} seconds.")

    async def question_helper(self, q: questions.Question, channel: discord.Channel):
        try:
            await asyncio.sleep(config["trivia"]["game_length"])
            await q.expire(self.client, channel)
            self.questions[channel].pop(q, None)
        except asyncio.CancelledError:
            pass

    async def on_message(self, message: discord.Message):
        if message.author == self.client.user:
            return
        if not self.questions[message.channel]:
            return

        for q, task in list(self.questions[message.channel].items()):
            if not q: continue

            points = await q.answer(self.client, message, self.user_db.get_score)
            if points:
                self.user_db.add_score(message.author.id, points)
                task.cancel()
                self.questions[message.channel].pop(q, None)

    async def on_ready(self):
        await self.client.change_presence(game=discord.Game(name="Use !trivia to play."))

    @contextmanager
    def lock_questions(self, channel):
        # dummy input to prevent the question queue from being empty when needed (allowing for !trivia spam)
        self.questions[channel][running] = True
        yield
        self.questions[channel].pop(running, None)


running = bool()  # its just a dummy value
