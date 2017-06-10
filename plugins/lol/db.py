# simple sqlite db for holding scores
# perhaps will look into using sqlalchemy
import sqlite3
from typing import Optional, List, Tuple


class TriviaDB(object):

    def __init__(self, file: str):
        self.conn: sqlite3.Connection = sqlite3.connect(file)
        self.db: sqlite3.Cursor = self.conn.cursor()
        self.db.execute("CREATE TABLE IF NOT EXISTS players(players_id INTEGER PRIMARY KEY, discord_id TEXT NOT NULL, score INTEGER)")

    def get_score(self, discord_id: str) -> Optional[int]:
        """Gets a player's score.
        
        Args:
            discord_id: The user id of the Discord member.

        Returns:
            Optional[int]: Score (int) if user exists, None otherwise.
        """
        self.db.execute("SELECT score FROM players WHERE discord_id=?;", (discord_id,)).fetchone()
        user: Tuple[int] = self.db.fetchone()
        return user[0] if user else None

    def add_score(self, discord_id: str, score: int) -> None:
        """Adds to a player's score
        
        Args:
            discord_id: The user id of the Discord member.
            score: The number of points to add.

        Returns:
            None
        """
        if not self.get_score(discord_id):
            self.db.execute("INSERT INTO players VALUES(NULL, ?, ?);", (discord_id, score))
        else:
            self.db.execute("UPDATE players SET score = score + ? WHERE discord_id=?", (score, discord_id))
        self.conn.commit()

    def get_top(self, num: int=10) -> List[Tuple[str, int]]:
        """Gets the top `num` players.
        
        Args:
            num: Number of top players to retrieve.

        Returns:
            List[Tuple[str, int]]: an ordered list (descending) of tuples of (discord_id, score).
        """
        self.db.execute("SELECT discord_id, score FROM players ORDER BY score DESC LIMIT ?;", (num,))
        return self.db.fetchall()
