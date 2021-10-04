""" This module implements the database backend for the TicTacToe application.
"""

from typing import Iterable
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


MAX_NAME_LENGTH = 16
PW_HASH_LENGTH  = 8

PLAYER_KEY = "player"
SCORE_KEY  = "score"


_Base = declarative_base()


class Player(_Base):
    """ Mapping class for players.
    """

    __tablename__ = "players"

    id    = sa.Column(sa.Integer, primary_key=True)
    name  = sa.Column(sa.String(MAX_NAME_LENGTH),
            nullable=False)
    score = sa.Column(sa.Integer, nullable=False)
    hash  = sa.Column(sa.String(PW_HASH_LENGTH),
            nullable=False)


    def __repr__(self) -> str:
        s  = f"Player(name={self.name}, score={self.score}, hash={self.hash})"
        return s


class Game(_Base):
    """ Mapping class for games.
    """

    __tablename__ = "games"

    id       = sa.Column(sa.Integer, primary_key=True)
    player_1 = sa.Column(sa.Integer, nullable=False)
    player_2 = sa.Column(sa.Integer, nullable=False)
    turn     = sa.Column(sa.Integer, nullable=False)
    board    = sa.Column(sa.Integer, nullable=False)


    def __repr__(self) -> str:
        s  = f"Game(id={self.id}, player_1={self.player_1}, "
        s += f"player_2={self.player_2}, turn={self.turn}, "
        s += f"board={self.board})"


class SQLiteDatabase:
    """ A database implementation based on SQLite and sqlalchemy.
    """

    def __init__(self, filename: str="game.db", clean: bool=False,
            check_same_thread: bool=True):
        """ - filename         : where the DB should be stored
            - clean            : create fresh database and wipes existing data
            - check_same_thread: en-/disable same thread checks of sqlite
        """
        self._engine = sa.create_engine(
                f"sqlite:///{filename}?check_same_thread={check_same_thread}")
        self._SessionFactory = sessionmaker(bind=self._engine)
        self._session = self._SessionFactory()  
        if clean:
            _Base.metadata.drop_all(self._engine, checkfirst=True)
        _Base.metadata.create_all(self._engine, checkfirst=True)


    def commit(self) -> None:
        """ Flushes session data to the database.
        """
        self._session.commit()


    def player_by_name(self, name: str) -> Optional[Player]:
        """ Fetches a Player instance for the specified name.

            - name: the player's name
        """
        s = self._session
        return s.query(Player).filter_by(name=name).first()


    def player_by_id(self, player_id: int) -> Optional[Player]:
        """ Fetches a Player instance for the given ID

            - player_id: the player's ID
        """
        s = self._session
        return s.query(Player).filter_by(id=player_id).first()


    def register_player(self, name: str, pw_hash: str):
        """ Adds a new player to the database.
            The caller must ensure that the name does not exist.

            - name   : the player's name
            - pw_hash: the player's password hash
        """
        player = Player(name=name, score=0, hash=pw_hash)
        self._session.add(player)
        self.commit()


    def add_game(self, player_1_name: str, player_2_name: str) -> int:
        """ Adds a game for the specified players to the database.
            Returns the created game's ID.

            - player_1_name: name of the first player
            - player_2_name: name of the second player
        """
        s = self._session
        p1_id = s.query(Player).filter_by(name=player_1_name).first().id
        p2_id = s.query(Player).filter_by(name=player_2_name).first().id
        game = Game(player_1=p1_id, player_2=p2_id, turn=p1_id, board=0)
        self._session.add(game)
        self.commit()
        self._session.refresh(game)
        return game.id


    def game_by_id(self, game_id: int) -> Optional[Game]:
        """ Returns a Game object by its ID.

            - game_id: the game's ID
        """
        s = self._session
        return s.query(Game).filter_by(id=game_id).first()


    def highscore(self, max_entries: int) -> Iterable[Player]:
        """ Returns an iterable of players.
            The list is sorted in descending order with respect to the player
            scores.

            - max_entries: the maximum number of entries in the returned list
        """
        s = self._session
        result = s.query(Player).order_by(
                sa.desc(Player.score)).limit(max_entries)
        return (x for x in result)
