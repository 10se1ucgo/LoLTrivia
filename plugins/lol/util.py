# messy shit dont read please
import json
from typing import *

import html2text
import cassiopeia as riotapi
from cassiopeia.core.staticdata import *
from cassiopeia.core.staticdata.champion import ChampionSpell, Skin
from cassiopeia.core.staticdata.common import Image
from cassiopeia.core.staticdata.rune import RunePath
from fuzzywuzzy import process

DDRAGON_BASE = f"http://ddragon.leagueoflegends.com/cdn/{riotapi.get_versions()[0]}"

SPELL_SCALINGS = {'attackdamage': "AD", 'bonusattackdamage': "**bonus** AD",
                  'armor': "Armor", 'bonusarmor': "**bonus** Armor",
                  'spellblock': "Magic Resist", 'bonusspellblock': "**bonus** Magic Resist",
                  'health': "Health", 'bonushealth': "**bonus** Health",
                  'spelldamage': "AP", "@dynamic.abilitypower": "AP"}
# unhandled special cases: (i have been unable to find out what these mean, api missing too much data :/)
# @dynamic.attackdamage @cooldownchampion

SANITIZER = html2text.HTML2Text()
SANITIZER.ignore_links = True
SANITIZER.body_width = 0

RUNE_TIER_NAMES = {
    RunePath.precision: ["Keystone", "Heroism", "Legend", "Combat"],
    RunePath.domination: ["Keystone", "Malice", "Tracking", "Hunter"],
    RunePath.sorcery: ["Keystone", "Artifact", "Excellence", "Power"],
    RunePath.resolve: ["Keystone", "Strength", "Resistance", "Vitality"],
    RunePath.inspiration: ["Keystone", "Contraption", "Tomorrow", "Beyond"]
}


class SkinInfo(NamedTuple):
    champ: Champion
    skin: Skin
    price: int
    currency: str
    date: str


# A lot of cass static data missing fields and bugs :(
def find_in_data(obj, name):
    for dto in obj._data.values():
        try:
            return getattr(dto, name)
        except AttributeError:
            continue


def get_champion_by_name(name: str) -> Tuple[Optional[Champion], int]:
    """Get a champion by name with fuzzy search.
    Args:
        name: Name of champion 

    Returns:
        Tuple[Optional[Champion], int]: Second element represents the query score (how close it is to the actual value).
    """
    return get_by_name(name, riotapi.get_champions())


def get_item(name_or_id: Union[str, int]) -> Tuple[Optional[Item], int]:
    """Get an item by name with fuzzy search.
    Args:
        name_or_id: Name or id of item 

    Returns:
        Tuple[Optional[Item], int]: Second element represents the query score (how close it is to the actual value).
    """
    items = riotapi.get_items()
    try:
        item = items[int(name_or_id)]
        return item, 100 if item else 0
    except (TypeError, KeyError, ValueError):
        return get_by_name(name_or_id, items)


TItem = TypeVar('TItem')


def get_by_name(name: str, items: Sequence[TItem]) -> Tuple[Optional[TItem], int]:
    """Get an item by name with fuzzy search.
    Args:
        name: Name of item
        items: The array of items to search from.

    Returns:
        Tuple[Optional[Item], int]: Second element represents the query score (how close it is to the actual value).
    """
    res = process.extractOne(name, {item: item.name for item in items}, score_cutoff=80)
    return (res[2], res[1]) if res else (None, 0)


def get_skin_by_name(name: str) -> Tuple[Optional[SkinInfo], int]:
    """Get a skin by name with fuzzy search.
    Args:
        name: Name of skin 

    Returns:
        Tuple[Optional[SkinInfo], bool]: Second element represents the query score (how close it is to the actual value).
    """
    res = process.extractOne(name, REVERSE_MAP_SKINS, score_cutoff=80)
    return (res[2], res[1]) if res else (None, 0)


def get_image_link(image: Image) -> str:
    return f"{DDRAGON_BASE}/img/{image.group}/{image.full}"


def parse_tooltip(spell: Union[ChampionSpell, SummonerSpell], tooltip: str) -> str:
    """
    Improved tooltip parser based on the built-in Cassiopeia `Spell.__replace_variables`
    """

    for dto in spell._data.values():
        try:
            costs_burn = dto.costBurn
            effects_burn = dto.effectBurn
            break
        except AttributeError:
            pass
    else:
        costs_burn = effects_burn = "?"

    tooltip = tooltip.replace("{{ cost }}", costs_burn)

    for x, effect in enumerate(effects_burn):
        tooltip = tooltip.replace(f"{{{{ e{x} }}}}", effect)

    try:
        variables = spell.variables
    except:
        # Bug in SummonerSpell.variables throws exception
        # TODO: submit patch
        variables = []

    for var in variables:
        if var.link in SPELL_SCALINGS:
            vals = '/'.join(f'{coeff * 100:g}' for coeff in var.coefficients)
            replacement = f"{vals}% {SPELL_SCALINGS[var.link]}"
        elif var.link == "@player.level":
            replacement = f"{var.coefficients[0]:g}-{var.coefficients[-1]:g} (based on level)"
        elif var.link == "@text":
            replacement = '/'.join(f'{coeff:g}' for coeff in var.coefficients)
        elif var.link == "@stacks":
            replacement = f"{spell.name} stacks"
        elif var.link == "@special.viw":
            replacement = f"1% per {'/'.join(f'{coeff:g}' for coeff in var.coefficients)} **Bonus** AD"
        elif var.link in {"@special.jaxrarmor", "@special.jaxrmr", "@special.BraumWArmor", "@special.BraumWMR"}:
            # idk why the spell tooltips even have these variables. the actual numbers are static inside the text...
            replacement = "bonus"
        elif var.link == "@special.nautilusq":
            replacement = ""
        else:
            replacement = f"{var.coefficients} {var.link}"
        tooltip = tooltip.replace(f"{{{{ {var.key} }}}}", replacement)

    return tooltip


def _load_skins() -> Dict[str, SkinInfo]:
    with open("data/skins.json", "r") as f:
        data: Dict[str, Tuple[str, str]] = json.load(f)

    skins: Dict[str, SkinInfo] = {}
    for champ in riotapi.get_champions():
        for skin in champ.skins:
            name = skin.name if skin.name != "default" else f"Classic {champ.name}"
            price, date = data.get(str(skin.id), (None, None))
            currency = "Gemstones" if price and price == 10 else "RP"  # SEND HELP
            skins[name] = SkinInfo(champ, skin, price, currency, date)

    return skins


def _load_quotes() -> Dict[str, List[str]]:
    with open("data/quotes.json", "r") as f:
        return json.load(f)


SKINS: Dict[str, SkinInfo] = _load_skins()
REVERSE_MAP_SKINS = {v: k for k, v in SKINS.items()}
QUOTES: Dict[str, List[str]] = _load_quotes()
