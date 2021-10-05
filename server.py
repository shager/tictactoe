from typing import Dict
from typing import Any
from typing import Optional
from typing import Tuple
from typing import Sequence
import os
from database import SQLiteDatabase
from database import Player
from database import Game


class Board:
    """ This class represents the player board.
        The board is comprised of 9 fields, like so:

            -------------
            | 0 | 1 | 2 |
            -------------
            | 3 | 4 | 5 |  <-- TicTacToe board
            -------------
            | 6 | 7 | 8 |
            -------------

        Every field can be written to, but not more than once.
        Internally, the board is represented as an 18 bit integer b, which is
        comprised of two 9 bit parts b1 and b2, one for each player:

                 MSB <---------------------------> LSB

        Bits:    8 7 6 5 4 3 2 1 0 | 8 7 6 5 4 3 2 1 0
            
                 |---------------|   |---------------|
                   Player 2 (b2)       Player 1 (b1)

        A bit in b is set, if a player has made its mark in the corresponding
        field of the TicTacToe board.
        This compact representation is used for efficiency reasons.


        Invariants:
        ===========

        (I1) At every time, (b1 & b2) == 0 must hold.
             This represents the fact that every field can be written by at
             most one player.

        (I2) At every time, there can be at most 9 set bits in b.
             This represents the fact that there are no more than 9 fields
             on the board.
    """

    def __init__(self, marks):
        self._b = marks
        # sanity check
        if (self.b1 & self.b2) > 0:
            raise ValueError("fields set more than once")


    b  = property(fget=lambda self: self._b)
    b1 = property(fget=lambda self: self._b & 0x1FF)
    b2 = property(fget=lambda self: (self._b >> 9) & 0x1FF)


    _WIN_PATTERNS = (
        #  876 543 210  <- field indices
        # rows
        0b_000_000_111, # 0 1 2
        0b_000_111_000, # 3 4 5
        0b_111_000_000, # 6 7 8
        # columns
        0b_001_001_001, # 0 3 6
        0b_010_010_010, # 1 4 7
        0b_100_100_100, # 2 5 8
        # diagonals
        0b_100_010_001, # 0 4 8
        0b_001_010_100  # 2 4 6
    )


    def is_player_win(self, player_num: int) -> bool:
        """ Checks if a player has won.

            - player_num: the player number
        """
        if player_num == 1:
            marks = self.b1
        elif player_num == 2:
            marks = self.b2
        else:
            raise ValueError("invalid player number")
        win = False
        for pattern in self._WIN_PATTERNS:
            win |= ((marks & pattern) == pattern)
        return win


    def is_win(self) -> bool:
        """ Checks if any player has won.
        """
        return self.is_player_win(1) or self.is_player_win(2)


    def is_finished(self) -> bool:
        """ Checks if the game is finished.
        """
        return self.is_full() or self.is_win()

        
    def set_field(self, pos: int, player_num: int) -> None:
        """ Marks a field on the board for a player.

            - pos       : the position to mark
            - player_num: the player that wants to make the mark
        """
        if player_num == 1:
            marks = self.b1
            other_marks = self.b2
            shift = 0
            other_shift = 9
        elif player_num == 2:
            marks = self.b2
            other_marks = self.b1
            shift = 9
            other_shift = 0
        else:
            raise ValueError("invalid player number")
        if self.is_set(pos):
            raise ValueError("field has already been set")
        marks |= (1 << pos)
        self._b = (marks << shift) | (other_marks << other_shift)


    def is_full(self) -> bool:
        """ Checks if every field on the board has been marked.
        """
        count = 0
        for shift in range(18):
            count += ((self.b >> shift) & 0x1)
        return count == 9


    def is_set(self, pos: int) -> bool:
        """ Checks if a position has been marked by any player.

            - pos: the position to check
        """
        return self.is_set_player(pos, 1) or self.is_set_player(pos, 2)
        

    def is_set_player(self, pos: int, player_num: int) -> bool:
        """ Checks if a position has been marked by player.

            - pos       : the position
            - player_num: the player number
        """
        if player_num == 1:
            marks = self.b1
        elif player_num == 2:
            marks = self.b2
        else:
            raise ValueError("invalid player number")
        return bool((marks >> pos) & 0x1)


    def free_fields(self) -> Sequence[int]:
        """ Returns a sequence of non-marked field indices.
        """
        both = self.b1 | self.b2
        indices = []
        for i in range(9):
            if (both >> i) & 0x1:
                continue
            indices.append(i)
        return indices


    def __str__(self):
        """ Returns a pretty-print of the game board.
        """
        dashes = "-------------"
        buf = ["", dashes]
        rows = ((0, 1, 2), (3, 4, 5), (6, 7, 8))
        for row in rows:
            row_buf = ["|"]
            for col in row:
                if self.is_set_player(col, 1):
                    mark = "x"
                elif self.is_set_player(col, 2):
                    mark = "o"
                else:
                    mark = " "
                row_buf.append(f" {mark} |")
            buf.append("".join(row_buf))
            buf.append(dashes)
        return os.linesep.join(buf)
            

Response = Dict[str, Any]


class Server:
    """ The Server class sits in between the frontend and the database.
        It is responsible for handling the actual game logic.

        It can be used with any (REST) frontend that solely relies on the 
        Server classes public interface methods.
    """

    STATUS_KEY   = "status"
    STATUS_OK    = "ok"
    STATUS_ERROR = "error"
    WHY_KEY      = "why"
    GAME_ID_KEY  = "game_id"
    TURN_KEY     = "turn"
    BOARD_KEY    = "board"
    NAME_KEY     = "name"
    SCORE_KEY    = "score"
    SCORES_KEY   = "scores"


    def __init__(self, database: SQLiteDatabase):
        """ - database: the database handle
        """
        self._db = database


    def register_player(self, name: str, pw_hash: str) -> Response:
        """ Adds a player to the database, if the name does not exist.

            - name   : the player's name
            - pw_hash: the player's password hash
        """
        if self._db.player_by_name(name=name) is not None:
            return self.error_msg(f"player {name} already exists")
        self._db.register_player(name, pw_hash)
        return self._ok()


    def create_game(self, player_1_name: str, pw_hash: str,
            player_2_name: str) -> Response:
        """ Creates a game for a tuple of players and writes it to the
            database.

            - player_1_name: name of first player
            - pw_hash      : password hash for first player
            - player_2_name: name of second player
        """
        player = self._db.player_by_name(player_1_name)
        if player is None:
            return self.error_msg(
                    f"player {player_1_name} cannot be authenticated")
        if player.hash != pw_hash:
            return self.error_msg(
                    f"player {player_1_name} cannot be authenticated")
        if player_1_name == player_2_name:
            return self.error_msg(f"please play against someone else")
        if self._db.player_by_name(player_2_name) is None:
            return self.error_msg(f"player {player_2_name} does not exist")
        game_id = self._db.add_game(player_1_name, player_2_name)
        return self._ok({self.GAME_ID_KEY: game_id})


    def highscore_list(self, max_entries: int) -> Response:
        """ Fetches the highscore list from the database.

            - max_entries: maximum number of entries in the list
        """
        players = self._db.highscore(max_entries)
        json_list = [{self.NAME_KEY: p.name, self.SCORE_KEY: p.score}
                for p in players]
        return self._ok({self.SCORES_KEY: json_list})


    def game_state(self, name: str, pw_hash: str, game_id: int) -> Response:
        """ Fetches a game's state from the database.
            Can only be done for a registered player.

            - name   : the player's name
            - pw_hash: the player's password hash
            - game_id: the game's ID
        """
        try:
            _, game = self._auth_player_and_game(name, pw_hash, game_id)
        except ValueError as error:
            return error.args[0]
        turn_player = self._db.player_by_id(game.turn)
        return self._ok({
            self.TURN_KEY : turn_player.name,
            self.BOARD_KEY: game.board
        })


    def make_turn(self, name: str, pw_hash: str, pos: int,
            game_id: int) -> Response:
        """ Updates a game by making a turn.
            Can only be done for a registered player associated to the game.

            - name   : the player's name
            - pw_hash: the player's password hash
            - pos    : the position to mark on the game board
            - game_id: the game's ID
        """
        # sanity checks
        try:
            player, game = self._auth_player_and_game(name, pw_hash, game_id)
        except ValueError as error:
            return error.args[0]
        if player.id != game.turn:
            return self.error_msg("not your turn")

        if player.id == game.player_1:
            player_num = 1
            next_id = game.player_2
        else:
            player_num = 2
            next_id = game.player_1

        board = Board(game.board)
        if board.is_finished():
            return self.error_msg("game finished")
        try:
            board.set_field(pos, player_num)
        except ValueError as error:
            return self.error_msg(str(error))
        game.board = board.b
        game.turn = next_id
        # check if game is finished
        if board.is_player_win(player_num):
            player.score += 1
        self._db.commit()
        return self._ok()


    def _auth_player_and_game(self, name: str, pw_hash: str,
            game_id: int) -> Tuple[Player, Game]:
        """ Fetches a player and game for the corresponding name and game IDs.

            - name   : the player's name
            - pw_hash: the player's password hash
            - game_id: the game's ID
        """
        player = self._db.player_by_name(name)
        if player is None:
            error = self.error_msg(f"player {name} cannot be authenticated")
            raise ValueError(error)
        if player.hash != pw_hash:
            error = self.error_msg(f"player {name} cannot be authenticated")
            raise ValueError(error)
        game = self._db.game_by_id(game_id)
        if player.id not in (game.player_1, game.player_2):
            raise ValueError(self.error_msg("no such game"))
        return player, game


    def error_msg(self, msg: str) -> Response:
        """ Helper method to create error messages.

            - msg: the error message
        """
        return {
            self.STATUS_KEY: self.STATUS_ERROR,
            self.WHY_KEY   : msg
        }


    def _ok(self, data: Optional[Response]=None) -> Response:
        """ Helper method to create return messages for successful operations.

            - data: a dict for various response data
        """
        msg = {self.STATUS_KEY: self.STATUS_OK}
        if data is not None:
            msg.update(data)
        return msg
