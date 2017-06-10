from cassiopeia import riotapi

import common
config = common.config[__name__]

riotapi.set_region(config["api_region"])
riotapi.set_api_key(config["api_key"])
from plugins.lol.trivia import LoLTrivia
