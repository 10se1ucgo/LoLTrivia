# messy shit dont read please
import json
from typing import *

import html2text
from cassiopeia import riotapi
from cassiopeia.type.core.staticdata import *
from fuzzywuzzy import process

DDRAGON_BASE = f"http://ddragon.leagueoflegends.com/cdn/{riotapi.get_versions()[0]}"

SPELL_SCALINGS = {'attackdamage': "AD", 'bonusattackdamage': "**Bonus** AD",
                  'armor': "Armor", 'bonusarmor': "**Bonus** Armor",
                  'spellblock': "Magic Resist", 'bonusspellblock': "**Bonus** Magic Resist",
                  'health': "Health", 'bonushealth': "**Bonus** Health",
                  'spelldamage': "AP"}
# unhandled special cases:
# @stacks @special.viw @special.jaxrarmor @special.BraumWArmor @special.jaxrmr @dynamic.abilitypower
# @special.nautilusq @dynamic.attackdamage @special.BraumWMR @cooldownchampion

# handled special cases: @player.level @text

SANITIZER = html2text.HTML2Text()
SANITIZER.ignore_links = True
SANITIZER.body_width = 0


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
    if isinstance(name_or_id, int) or name_or_id.isdigit():
        item = riotapi.get_item(int(name_or_id))
        return (item, 100 if item else 0)
    return get_by_name(name_or_id, riotapi.get_items())


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


SkinInfo = NamedTuple("SkinInfo", champ=Champion, skin=Skin, price=str, date=str)


def get_skin_by_name(name: str) -> Tuple[Optional[SkinInfo], int]:
    """Get a skin by name with fuzzy search.
    Args:
        name: Name of skin 

    Returns:
        Tuple[Optional[SkinInfo], bool]: Second element represents the query score (how close it is to the actual value).
    """
    res = process.extractOne(name, {v: k for k, v in SKINS.items()}, score_cutoff=80)
    return (res[2], res[1]) if res else (None, 0)


def get_image_link(image: Image) -> str:
    return f"{DDRAGON_BASE}/img/{image.group}/{image.link}"


def parse_tooltip(spell: Union[Spell, SummonerSpell], tooltip: str) -> str:
    """
    Improved tooltip parser based on the built-in Cassiopeia `Spell.__replace_variables`
    """
    tooltip = tooltip.replace("{{ cost }}", spell.cost_burn)

    for x, effect in enumerate(spell.effect_burn):
        tooltip = tooltip.replace(f"{{{{ e{x} }}}}", effect)

    for var in spell.variables:
        if var.link in SPELL_SCALINGS:
            vals = '/'.join(f'{coeff:g}' for coeff in var.coefficients)
            replacement = f"{vals}% {SPELL_SCALINGS[var.link]}"
        elif var.link == "@player.level":
            replacement = f"{var.coefficients[0]:g}-{var.coefficients[-1]:g} (based on level)"
        elif var.link == "@text":
            replacement = '/'.join(f'{coeff:g}' for coeff in var.coefficients)
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
            skins[name] = SkinInfo(champ, skin, *data.get(str(skin.id), (None, None)))

    return skins


def _load_quotes() -> Dict[str, List[str]]:
    with open("data/quotes.json", "r") as f:
        return json.load(f)


SKINS: Dict[str, SkinInfo] = _load_skins()
QUOTES: Dict[str, List[str]] = _load_quotes()
