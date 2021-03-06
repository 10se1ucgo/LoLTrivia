import random
from collections import Counter
from typing import *

import discord
import cassiopeia as riotapi
# from cassiopeia.core.common import Map
from cassiopeia.core.staticdata import *
from cassiopeia.core.staticdata.champion import ChampionSpell, Skin
from fuzzywuzzy import fuzz

from . import util, config

ALLOWED_MODES: Set[str] = {mode.upper() for mode in config["trivia"]["allowed_modes"]}
ALLOWED_SPELLS: List[SummonerSpell] = \
    [spell for spell in riotapi.get_summoner_spells() if not ALLOWED_MODES.isdisjoint(util.find_in_data(spell, "modes"))]

# ALLOWED_MAPS: Set[str] = \
#     {str(Map[map.lower()].value) if not map.isdigit() else map for map in config["trivia"]["allowed_maps"]}
ALLOWED_MAPS: Set[int] = \
    {int(riotapi.get_maps()[map].id) if not map.isdigit() else int(map) for map in config["trivia"]["allowed_maps"]}

print(ALLOWED_MAPS)
ALLOWED_ITEMS: List[Item] = []
for item in riotapi.get_items():
    # print(list(map.id for map in item.maps))
    if not ALLOWED_MAPS.isdisjoint(int(map.id) for map in item.maps):
        ALLOWED_ITEMS.append(item)

PERCENT_STATS: List[str] = ["percent", "spell_vamp", "life_steal", "tenacity", "critical", "attack_speed", "cooldown"]

class Question(object):
    """A trivia question
    """
    def __init__(self, title: str, desc: Optional[str], a: Union[str, Iterable[str]], *,
                 extra: str="", fuzzywuzzy: bool=True, modifier: Callable[[str], str]=lambda x: x):
        """Create new Question object

        Args:
            title: The question title.
            desc: The question description
            a: The correct answer(s) to the question.
            
            extra: Extra text to say after the correct answer in the expire/answer message.
            fuzzywuzzy: Whether or not to use fuzzy string matching.
            modifier: a function to call on each answer input (for pre-processing)
        """
        self.q: discord.Embed = discord.Embed(title=title, description=desc, color=discord.Color.blue())
        self.a: List[str] = list(a) if not isinstance(a, str) else [a]

        self.extra: str = extra
        self.fuzzywuzzy: bool = fuzzywuzzy
        self.modifier: Callable[[str], str] = modifier

        self.active: bool = True

    async def say(self, channel: discord.TextChannel):
        """Say the question in chat (and the embed if specified)
        
        Args:
            channel: the channel to send it to.

        Returns:
            None
        """
        await channel.send(self.q.title, embed=self.q)

    async def expire(self, channel: discord.TextChannel):
        """Expire the question and end the game in chat.
        
        Args:
            channel: the channel to send the expire message to.

        Returns:
            None
        """
        self.active = False
        correct: str = '/'.join(random.sample(self.a, min(3, len(self.a)))) + ('/etc...' if len(self.a) > 3 else '')
        await channel.send(f"Time's up! The correct answer was '{correct}'{self.extra}.")

    async def answer(self, message: discord.Message, get_score: Callable[[str], int]) -> int:
        if not self.active: return False

        msg: str = self.modifier(message.content).lower()

        for ans in self.a:
            mod_ans: str = self.modifier(ans).lower()

            if (self.fuzzywuzzy and fuzz.ratio(mod_ans, msg) >= 90) or (mod_ans == msg):
                break
        else:
            return False

        self.active = False
        points: int = config['trivia']['points']
        await message.channel.send(
            f"Correct answer '{ans}'{self.extra} by {message.author.mention}! +{points} points"
            f" (new score: {(get_score(message.author.id) or 0) + points})"
        )
        return points

    def set_thumbnail(self, *args, **kwargs) -> 'Question':
        self.q.set_thumbnail(*args, **kwargs)
        return self

    def set_image(self, *args, **kwargs) -> 'Question':
        self.q.set_image(*args, **kwargs)
        return self

    def add_field(self, *args, **kwargs) -> 'Question':
        self.q.add_field(*args, **kwargs)
        return self

    def __bool__(self) -> bool:
        return self.active


def censor_name(text: str, *args: str, replacement: str="XXXXXXX") -> str:
    for word in args:
        text = text.replace(word, replacement)
    return text


# A lot of these use very similar "boilerplate" (getting the champ, spells, etc).
# Hesitant to combine similar ones and use random.choice((Question(), Question(), ...)) as it changes
# the probability of getting certain question types.
def champ_from_spell() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    spell: ChampionSpell = random.choice(champ.spells)

    return Question(f"Which champion has an ability called '{spell.name}'?", None, champ.name,
                    extra=f" ({spell.keyboard_key.name})")


def spell_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    spell: ChampionSpell = random.choice(champ.spells)

    return Question(f"What's the name of {champ.name}'s {spell.keyboard_key.name}?", None, spell.name)\
        .set_thumbnail(url=util.get_image_link(spell.image_info))


def spell_from_desc() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    spell: ChampionSpell = random.choice(champ.spells)
    desc: str = censor_name(util.SANITIZER.handle(spell.description), champ.name, spell.name)

    return Question("What's the name of this spell?", desc, spell.name,
                    extra=f" ({champ.name} {spell.keyboard_key.name})") \
        .set_thumbnail(url=util.get_image_link(spell.image_info))


def champ_from_title() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"Which champion is '{champ.title}'?", None, champ.name)


def title_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    def remove_the(text: str) -> str:
        return text[3:].strip() if text.lower().startswith("the") else text

    return Question(f"What is {champ.name}'s title?", None, champ.title, modifier=remove_the)\
        .set_thumbnail(url=util.get_image_link(champ.image))


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
    skins: str = censor_name('\n'.join([f'- "{skin.name}"' for skin in champ.skins[1:]]), *champ.name.split())

    return Question("Which champion's skins are these?", skins, champ.name)


def champ_from_splash() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    # skins[0] is the classic skin
    skin: Skin = random.choice(champ.skins[1:])

    return Question("Which skin is this?", None, skin.name).set_image(url=skin.loading_image_url)


def champ_from_passive() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())
    desc: str = util.SANITIZER.handle(censor_name(champ.passive.description, champ.name))

    return Question("Which champion's passive is this?", desc, champ.name)


def passive_from_champ() -> Question:
    champ: Champion = random.choice(riotapi.get_champions())

    return Question(f"What is the name of {champ.name}'s passive?", None, champ.passive.name).\
        set_thumbnail(url=util.get_image_link(champ.passive.image_info))


def summ_from_tooltip() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)
    desc: str = util.SANITIZER.handle(censor_name(util.parse_tooltip(spell, spell.tooltip), spell.name))

    return Question("Which summoner spell is this?", desc, spell.name)


def cd_from_summ() -> Question:
    spell: SummonerSpell = random.choice(ALLOWED_SPELLS)

    return Question(f"What's the base cool down of '{spell.name}'?", None, str(spell.cooldowns[0]), fuzzywuzzy=False).\
        set_thumbnail(url=util.get_image_link(spell.image))


def item_buy_gold() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if item.gold.total > 0])

    return Question(f"How much is '{item.name}'?", None, str(item.gold.total), fuzzywuzzy=False).\
        set_thumbnail(url=util.get_image_link(item.image))


def item_text() -> Question:
    item: Item = random.choice(ALLOWED_ITEMS)

    return Question("Which item is this?", util.SANITIZER.handle(item.plaintext), item.name).\
        add_field(name="Stats", value=censor_name(util.SANITIZER.handle(item.description), item.name))


# TODO: Update for new Cass!
# TODO: Implement regex stat parsing into new Cass!
# def item_stat() -> Question:
#     item: Item = random.choice([item for item in ALLOWED_ITEMS if getattr(item, 'stats')])
#     stats: List[str] = [stat for stat in item.stats._ItemStats__stats if getattr(item.stats, stat, 0.0) != 0.0]
#     if not stats:
#         return item_stat()
#
#     stat: str = random.choice(stats)
#     val: Union[int, float] = getattr(item.stats, stat)
#     p_stat = False
#     if any(x in stat for x in PERCENT_STATS):
#         p_stat = True
#         val *= 100
#
#     return Question(f"How much **{stat.replace('_', ' ').replace('percent', '%')}** does '{item.name}' give?", None,
#                     f"{val:.0f}{'%' if p_stat else ''}", modifier=lambda ans: ans.strip('%')).\
#         set_thumbnail(url=util.get_image_link(item.image))


def items_from_component() -> Question:
    item: Item = random.choice([item for item in ALLOWED_ITEMS if item.builds_into])

    return Question("What is one item this builds into?", item.name, {c.name for c in item.builds_into}).\
        set_thumbnail(url=util.get_image_link(item.image))


def item_from_components() -> Question:
    items: List[Item] = [item for item in ALLOWED_ITEMS if len(item.builds_from) > 1]

    components: Counter[Item] = Counter(random.choice(items).builds_from)
    components_str: str = '\n'.join([f"- {item.name} x {number}" for item, number in components.items()])

    correct_items: Set[str] = {item.name for item in items if Counter(item.builds_from) == components}

    return Question("What is one item that builds from these items?", components_str, correct_items)


def rune_from_desc() -> Question:
    rune: Rune = random.choice(riotapi.get_runes())
    desc: str = censor_name(util.SANITIZER.handle(rune.long_description), *rune.name.split())

    return Question("What's the name of this rune?", desc, rune.name, extra=f" ({rune.path.value} Tree)")


def tree_from_rune() -> Question:
    rune: Rune = random.choice(riotapi.get_runes())

    return Question(f"What tree is {rune.name} from?", None, rune.path.value)


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
    cd_from_summ,
    item_buy_gold,
    item_text,
    # item_stat,
    items_from_component,
    item_from_components,
    rune_from_desc,
    tree_from_rune
)
