# LoLTrivia
A discord LoL Trivia bot written in Python, based on
[the original #r/leagueoflegends IRC version](https://github.com/SaschaMann/TriviaBot/)

[Invite Link](https://discordapp.com/oauth2/authorize?client_id=272459645673668608&scope=bot&permissions=101440) (BETA: Please report bugs on the GitHub issue tracker!)


the code needs a cleanup pls no flamerino ty

# USAGE
- Base command: `!trivia [num=1]` - Starts a game of LoL Trivia.
    - `[num]` specifies the number of games to play. Max 15. Only staff* can play more than 5 game.
    - 10 second cooldown.

- `!trivia force [num] [force_index]` - Staff* only, force starts a game of trivia, regardless of cooldown.
    - If `[force_index]` is specified, that specific question type will be played.

- `!trivia cancel` - Staff* only, cancels all current games in the channel.

- `!trivia info <arg1> [arg2]` - Returns info on a champion, skin or item (best guess).
    - If `[arg1]` is the name of a champion, returns info on the champion (title, passive, spells).
        - Additionally, `[arg2]` can be specified as one of "Q", "W", "E", "R", "P", returning specific info about that spell.

    - If `[arg1]` is the name of a skin, returns info on price/release date as well as splash art. Can specify [arg2] as "loading" to get loading screen slice.

    - `[arg1]` can also be the name of a summoner spell, rune, mastery or an item.

- `!trivia <champ/skin/item/mastery/summ/rune> <arg> [arg2]` - `!trivia info` but forced to a specific type.

- `!trivia top` - Returns a list of the top 10 players and their scores.

- `!trivia score [user]` - Returns the score of `[user]`. Defaults to you.

- If the bot is given a role named `DisableTrivia`, it will disable the `!trivia` game. (Info commands will continue to function, however)

\*Those who have the "Manage Messages" permission.

***These next two sections are only for those who plan on running their own instance of the bot.
Most users can just invite the public bot to their server***

# REQUIREMENTS
* Python 3.6
* [discord.py](https://github.com/Rapptz/discord.py) - Discord API wrapper
* [cassiopeia **< 3.0**](https://github.com/meraki-analytics/cassiopeia) - Riot API wrapper
* [html2text](https://github.com/aaronsw/html2text) - Used to sanitize certain API results (tooltips, descriptions, etc)
* [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy) - Fuzzy string matching for trivia questions

# RUNNING THE BOT
1. Rename config.example.json to config.json
2. Fill in the "discord_token", "owner_id", "api_region" and "api_key" sections.
Modify anything else to your content.
    - [Valid values for `allowed_modes` and `allowed_maps` can be found here](https://developer.riotgames.com/game-constants.html#mapNames)
    - Note that `allowed_maps` will also accept integer mapids.
3. You need to generate your own `quotes.json` and `skins.json` in the `data` folder.
There are example files showing the format. I will eventually make them optional.
4. Run `run.py`.

# TODO

- [ ] Move to new cassiopeia (new version missing certain things for now)

# DISCLAIMER

LoLTrivia isn’t endorsed by Riot Games and doesn’t reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.
