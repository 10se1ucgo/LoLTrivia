import random
from typing import Optional, Callable, Tuple, Union, List

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

PERCENT_STATS = ["percent", "spell_vamp", "life_steal", "tenacity", "critical", "attack_speed", "cooldown"]

class Question(object):
    """A trivia question
    """
    def __init__(self, title: str, desc: Optional[str], a: Union[str, List[str]], *,
                 extra: str="", fuzzywuzzy: bool=True, modifier: Callable[[str], str]=lambda x: x):
        """init. blah.
        
        Args:s
            title: The question title.
            desc: The question description
            a: The correct answer(s) to the question.
            
            extra: Extra text to say after the correct answer in the expire/answer message.
            fuzzywuzzy: Whether or not to use fuzzy string matching.
            modifier: a function to call on each answer input (for pre-processing)
        """
        self.q = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        self.a = a if isinstance(a, List) else [a]

        self.extra = extra
        self.fuzzywuzzy = fuzzywuzzy
        self.modifier = modifier

        self.answered = False

    async def say(self, client: discord.Client, channel: discord.Channel):
        """Say the question in chat (and the embed if specified)
        
        Args:
            client: the bot to send with.
            channel: the channel to send it to.

        Returns:
            None
        """
        await client.send_message(channel, embed=self.q)

    async def expire(self, client: discord.Client, channel: discord.Channel):
        """Expire the question and end the game in chat.
        
        Args:
            client: the bot to send the expire message with.
            channel: the channel to send it to.

        Returns:
            None
        """
        self.answered = True
        a_str = '/'.join(random.sample(self.a, min(3, len(self.a)))) + ('/etc...' if len(self.a) > 3 else '')
        await client.send_message(channel, f"Time's up! The correct answer was '{a_str}'{self.extra}.")

    async def answer(self, client: discord.Client, message: discord.Message, get_score: Callable[[str], int]) -> int:
        if self.answered: return False

        msg = self.modifier(message.content).lower()

        for ans in self.a:
            mod_ans = self.modifier(ans).lower()

            if (self.fuzzywuzzy and fuzz.ratio(mod_ans, msg) >= 90) or (mod_ans == msg):
                break
        else:
            return False

        self.answered = True
        points = config['trivia']['points']
        await client.send_message(message.channel,
                                  f"Correct answer '{ans}'{self.extra} by {message.author.mention}! +{points} points"
                                  f" (new score: {(get_score(message.author.id) or 0) + points})")
        return points

    def set_thumbnail(self, *args, **kwargs):
        self.q.set_thumbnail(*args, **kwargs)
        return self

    def set_image(self, *args, **kwargs):
        self.q.set_image(*args, **kwargs)
        return self

    def add_field(self, *args, **kwargs):
        self.q.add_field(*args, **kwargs)
        return self

    def __bool__(self):
        return not self.answered


def censor_name(text: str, *args, replacement: str="XXXXXXX") -> str:
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

    return Question(f"Which champion has an ability called '{spell.name}'?", None, champ.name,
                    extra=f" ({'QWER'[index]})")


def spell_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    index: int = random.randrange(len(champ.spells))
    spell: Spell = champ.spells[index]

    return Question(f"What's the name of {champ.name}'s {'QWER'[index]}?", None, spell.name).\
        set_thumbnail(url=util.get_image_link(spell.image))


def spell_from_desc() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    index: int = random.randrange(len(champ.spells))
    spell: Spell = champ.spells[index]
    desc: str = censor_name(util.SANITIZER.handle(spell.description), champ.name, spell.name)

    return Question("What's the name of this spell?", desc, spell.name, extra=f" ({champ.name} {'QWER'[index]})").\
        set_thumbnail(url=util.get_image_link(spell.image))


def champ_from_title() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"Which champion is '{champ.title}'?", None, champ.name)


def title_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    def remove_the(text: str) -> str:
        text = text.lower()
        return text[3:].strip() if text.startswith("the") else text

    return Question(f"What is {champ.name}'s title?", None, champ.title, modifier=remove_the).\
        set_thumbnail(url=util.get_image_link(champ.image))


def champ_from_lore() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    lore: str = censor_name(util.SANITIZER.handle(champ.blurb), champ.name)

    return Question("Which champion's lore is this?", lore, champ.name)


def champ_from_quote() -> Question:
    champ_name: str = random.choice(list(util.QUOTES.keys()))
    quote: str = random.choice(util.QUOTES[champ_name])

    return Question("Which champion says the following line?", quote, champ_name)


def champ_from_skins() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    skins: str = censor_name('- ' + '\n- '.join(f'"{skin.name}"' for skin in champ.skins[1:]), *champ.name.split())

    return Question("Which champion's skins are these?", skins, champ.name)


def champ_from_splash() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    # skins[0] is the classic skin
    skin: Skin = random.choice(champ.skins[1:])

    return Question("Which skin is this?", None, skin.name).set_image(url=skin.loading)


def champ_from_passive() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    desc: str = censor_name(champ.passive.sanitized_description, champ.name)

    return Question("Which champion's passive is this?", desc, champ.name)


def passive_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"What is the name of {champ.name}'s passive?", None, champ.passive.name).\
        set_thumbnail(url=util.get_image_link(champ.passive.image))


def summ_from_tooltip() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)
    desc: str = censor_name(util.parse_tooltip(spell, util.SANITIZER.handle(spell.tooltip)), spell.name)

    return Question("Which summoner spell is this?", desc, spell.name)


def summ_cd() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)

    return Question(f"What's the base cool down of '{spell.name}'?", None, spell.cooldown_burn, fuzzywuzzy=False).\
        set_thumbnail(url=util.get_image_link(spell.image))


def item_buy_gold() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if item.gold.total > 0])

    return Question(f"How much is '{item.name}'?", None, str(item.gold.total), fuzzywuzzy=False).\
        set_thumbnail(url=util.get_image_link(item.image))


def item_text() -> Question:
    item: Item = random.choice(ALLOWED_ITEMS)

    return Question("Which item is this?", util.SANITIZER.handle(item.blurb), item.name).\
        add_field(name="Stats", value=censor_name(util.SANITIZER.handle(item.description), item.name))


def item_stat() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if getattr(item, 'stats')])
    stats = [stat for stat in item.stats._ItemStats__stats if getattr(item.stats, stat, 0.0) != 0.0]
    if not stats:
        return item_stat()

    stat = random.choice(stats)
    val = getattr(item.stats, stat)
    p_stat = False
    if any(x in stat for x in PERCENT_STATS):
        p_stat = True
        val *= 100

    return Question(f"How much **{stat.replace('_', ' ').replace('percent', '%')}** does '{item.name}' give?", None,
                    f"{val:.0f}{'%' if p_stat else ''}", modifier=lambda ans: ans.strip('%')).\
        set_thumbnail(url=util.get_image_link(item.image))


def item_from_component() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if item.component_of])

    return Question("What is one item this builds into?", item.name, [c.name for c in item.component_of]).\
        set_thumbnail(url=util.get_image_link(item.image))


def item_from_components() -> Question:
    items: List[Item] = [item for item in ALLOWED_ITEMS if len(item.components) > 1]
    item = random.choice(items)

    components = {comp.name for comp in item.components}
    components_str = '- ' + '\n- '.join(comp.name for comp in item.components)
    correct_items = []

    for i in items:
        if {comp.name for comp in i.components} == components:
            correct_items.append(i.name)

    return Question("What is one item that builds from these items?", components_str, correct_items)


def mastery_from_desc() -> Question:
    mastery: Mastery = random.choice(riotapi.get_masteries())
    desc: str = censor_name(util.SANITIZER.handle(mastery.descriptions[-1]), *mastery.name.split())

    return Question("What's the name of this mastery?", desc, mastery.name, extra=f" ({mastery.tree.value} Tree)")


def tree_from_mastery() -> Question:
    mastery: Mastery = random.choice(riotapi.get_masteries())

    return Question(f"What tree is {mastery.name} from?", None, mastery.tree.value)


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
    item_from_component,
    item_from_components,
    mastery_from_desc,
    tree_from_mastery
)
