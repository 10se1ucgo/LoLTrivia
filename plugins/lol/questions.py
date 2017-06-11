import random
from typing import Optional, Callable, Tuple

import discord
from cassiopeia import riotapi
from cassiopeia.type.core.common import Map
from cassiopeia.type.core.staticdata import *
from fuzzywuzzy import fuzz

from plugins.lol import util, config

ALLOWED_MODES = {mode.upper() for mode in config["trivia"]["allowed_modes"]}
ALLOWED_SPELLS = [spell for spell in riotapi.get_summoner_spells() if not ALLOWED_MODES.isdisjoint(spell.data.modes)]

# this is readable, right? :^)
ALLOWED_MAPS = {str(Map[map.lower()].value) if not map.isdigit() else map for map in config["trivia"]["allowed_maps"]}
ALLOWED_ITEMS = [item for item in riotapi.get_items()
                 if not ALLOWED_MAPS.isdisjoint(map for map in item.data.maps if item.data.maps[map])]
# ok that looks pretty confusing so let me break it down
# item.data.maps returns a dict e.g. {'11': True, '12': True, '14': False, '16': False, '8': True, '10': True}
# map for map in item.data.maps if item.data.maps[map] returns all the keys that are True, so in this case  it returns
# ['11', '12', '8', '10']. ALLOWED_MAPS is a set e.g. {'12', '11'}.
# and {'12', '11'}.isdisjoint(['11', '12', '8', '10']) returns True if the set has no elements in common with other.
# if this really needed 5 lines of explanation then perhaps i should rewrite it xd

PERCENT_STATS = ("percent", "spell_vamp", "life_steal", "tenacity", "critical", "attack_speed", "cooldown")

class Question(object):
    """A trivia question
    """
    def __init__(self, q: Optional[str], a: str, *,
                 extra: str= "", fuzzywuzzy: bool=True, embed: discord.Embed=None, modifier: Callable[[str], str]=None):
        """init. blah.
        
        Args:
            q: The question message.
            a: The answer to the question.
            
            extra: Extra test to say after the correct answer in the expire/answer message.
            fuzzywuzzy: Whether or not to use fuzzy string matching.
            embed: An embed to display.
            modifier: a function to call on each answer input (for pre-processing)
        """
        self.q = q
        self.a = a

        self.extra = extra
        self.fuzzywuzzy = fuzzywuzzy
        self.embed = embed
        self.modifier = modifier or (lambda x: x)

        self.answered = False

    async def say(self, client: discord.Client, channel: discord.Channel):
        """Say the question in chat (and the embed if specified)
        
        Args:
            client: the bot to send with.
            channel: the channel to send it to.

        Returns:
            None
        """
        await client.send_message(channel, self.q, embed=self.embed)

    async def expire(self, client: discord.Client, channel: discord.Channel):
        """Expire the question and end the game in chat.
        
        Args:
            client: the bot to send the expire message with.
            channel: the channel to send it to.

        Returns:
            None
        """
        self.answered = True
        await client.send_message(channel, f"Time's up! The correct answer was '{self.a}'{self.extra}.")

    async def answer(self, client: discord.Client, message: discord.Message, score: Callable) -> int:
        if self.answered: return False

        msg = self.modifier(message.content).lower()

        if self.fuzzywuzzy:
            if fuzz.ratio(self.a.lower(), msg) < 90:
                return False
        elif self.a.lower() != msg:
            return False

        self.answered = True
        points = config['trivia']['points']
        await client.send_message(message.channel,
                                  f"Correct answer '{self.a}'{self.extra} by {message.author.mention}! +{points} points"
                                  f" (new score: {score() + points})")
        return points

    def __bool__(self):
        return not self.answered


def censor_name(text: str, *args, replacement: str="-------") -> str:
    for word in args:
        text = text.replace(word, replacement)
    return text


# A lot of these use very similar "boilerplate" (getting the champ, spells, etc).
# Hesitant to combine similar ones and use random.choice((Question(), Question(), ...)) as it changes
# the probability of getting certain question types.
def champ_from_spell() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    index: int = random.randrange(len(champ.spells))
    spell: Spell = champ.spells[index]

    return Question(f"Which champion has an ability called '{spell.name}'?", champ.name,
                    extra=f" ({'QWER'[index]})")


def spell_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    index: int = random.randrange(len(champ.spells))
    spell: Spell = champ.spells[index]

    return Question(f"What's the name of {champ.name}'s {'QWER'[index]}?", spell.name)


def spell_from_desc() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    index: int = random.randrange(len(champ.spells))
    spell: Spell = champ.spells[index]
    desc: str = censor_name(util.SANITIZER.handle(spell.description), champ.name, spell.name)

    embed = discord.Embed(title=f"???",
                          description=desc,
                          type="rich", color=discord.Color.blue())
    embed.set_thumbnail(url="https://avatar.leagueoflegends.com/Hi/Riot.png")

    return Question(f"What's the name of this spell?", spell.name, embed=embed,
                    extra=f" ({champ.name} {'QWER'[index]})")


def champ_from_title() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"Which champion is '{champ.title}'?", champ.name)


def title_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"What is {champ.name}'s title?", champ.title)


def champ_from_lore() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    embed = discord.Embed(title=f"???",
                          description=censor_name(util.SANITIZER.handle(champ.blurb), champ.name),
                          type="rich", color=discord.Color.blue())
    embed.set_thumbnail(url="https://avatar.leagueoflegends.com/Hi/Riot.png")

    return Question(f"Which champion's lore is this?", champ.name, embed=embed)


def champ_from_quote() -> Question:
    champ_name: str = random.choice(list(util.QUOTES.keys()))
    quote = random.choice(util.QUOTES[champ_name])

    return Question(f"Which champion says the following line? {quote}", champ_name)


def champ_from_skins() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    skins: str = censor_name(', '.join(f'"{skin.name}"' for skin in champ.skins[1:]), *champ.name.split())

    return Question(f"Which champion's skins are these? {skins}", champ.name)


def champ_from_splash() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    # skins[0] is the classic skin
    skin: Skin = random.choice(champ.skins[1:])

    embed = discord.Embed(title=f"Which skin is this?",
                          type="rich", color=discord.Color.blue())
    embed.set_image(url=skin.loading)

    return Question(None, skin.name, embed=embed)


def champ_from_passive() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    desc: str = censor_name(champ.passive.sanitized_description, champ.name)

    return Question(f"Which champion's passive is this? '{desc}'", champ.name)


def passive_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"What is the name of {champ.name}'s passive?", champ.passive.name)


def summ_from_tooltip() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)
    desc: str = censor_name(util.parse_tooltip(spell, util.SANITIZER.handle(spell.tooltip)), spell.name)

    embed = discord.Embed(title=f"???",
                          description=desc,
                          type="rich", color=discord.Color.blue())
    embed.set_thumbnail(url="http://avatar.leagueoflegends.com/Hi/Riot.png")

    return Question(f"Which summoner spell is this?", spell.name, embed=embed)


def summ_cd() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)

    return Question(f"What's the base cool down of '{spell.name}'?", spell.cooldown_burn, fuzzywuzzy=False)


def item_buy_gold() -> Question:
    item: Item = random.choice(ALLOWED_ITEMS)

    return Question(f"How much is '{item.name}'?", str(item.gold.total), fuzzywuzzy=False)


def item_text() -> Question:
    item: Item = random.choice(ALLOWED_ITEMS)

    embed = discord.Embed(title=f"???",
                          description=util.SANITIZER.handle(item.blurb),
                          type="rich", color=discord.Color.blue())
    embed.set_thumbnail(url="http://avatar.leagueoflegends.com/Hi/Riot.png")
    embed.add_field(name="Stats", value=censor_name(util.SANITIZER.handle(item.description), item.name))

    return Question(f"Which item is this?", item.name, embed=embed)


def item_stat() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if getattr(item, 'stats')])
    stats = [stat for stat in item.stats._ItemStats__stats if getattr(item.stats, stat, 0.0) != 0.0]
    if not stats:
        return item_stat()

    stat = random.choice(stats)
    val = getattr(item.stats, stat)
    if any(x in stat for x in PERCENT_STATS):
        val *= 100

    return Question(f"How much **{stat.replace('_', ' ').replace('percent', '%')}** does '{item.name}' give?",
                    f"{val:.0f}", modifier=lambda x: x.strip('%'))


def get_random_question(force_index: int=None) -> Question:
    if force_index is not None and (0 <= force_index < len(_questions)):
        return _questions[force_index]()
    return random.choice(_questions)()

_questions: Tuple[Callable[[], Question]] = (
    champ_from_spell,
    spell_from_champ,
    spell_from_desc,
    champ_from_title,
    title_from_champ,
    champ_from_lore,
    champ_from_quote,
    champ_from_skins,
    champ_from_splash,
    champ_from_passive,
    passive_from_champ,
    summ_from_tooltip,
    summ_cd,
    item_buy_gold,
    item_text,
    item_stat,
)
