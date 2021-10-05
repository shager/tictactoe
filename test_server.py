""" This module contains tests for the control logic within the game server.
"""

import os
import pytest
from server import Server
from server import Board
from database import SQLiteDatabase
from database import MAX_NAME_LENGTH
from database import PW_HASH_LENGTH

from tst_utils import random_string
from tst_utils import random_hex_string
from tst_utils import clean_file


class TestBoard:
    """ Tests for the game board representation.
    """

    @pytest.mark.parametrize("marks",
        [
            0,
            0b_000_000_111_111_000_000,
            0b_100_010_001_001_100_100,
        ]
    )
    def test_ascii(self, marks):
        board = Board(marks)
        print(str(board))


    @pytest.mark.parametrize("marks, player_1_win, player_2_win",
        [
            (0b_000_000_000_000_000_000, False, False),
            (0b_111_000_000_000_000_000, False, True ),
            (0b_000_111_000_000_000_000, False, True ),
            (0b_000_000_111_000_000_000, False, True ),
            (0b_000_000_000_111_000_000, True,  False),
            (0b_000_000_000_000_111_000, True,  False),
            (0b_000_000_000_000_000_111, True,  False),
            (0b_000_000_000_001_001_001, True,  False),
            (0b_100_010_001_000_001_100, False, True ),
            (0b_100_100_001_001_010_100, True , False),
        ]
    )
    def test_is_player_win(self, marks, player_1_win, player_2_win):
        board = Board(marks)
        assert board.is_player_win(1) == player_1_win
        assert board.is_player_win(2) == player_2_win


    @pytest.mark.parametrize("marks, full", 
        [
            (0b_000_000_000_000_000_000, False),
            (0b_000_111_000_111_000_111, True),
            (0b_100_001_010_011_010_101, False),
            (0b_100_101_010_011_010_101, True),
        ]
    )
    def test_is_full(self, marks, full):
        board = Board(marks)
        assert board.is_full() == full


    @pytest.mark.parametrize("marks, exp", [
        (0b_000_000_000_000_000_000, list(range(9))),
        (0b_000_000_001_100_000_100, [1, 3, 4, 5, 6, 7]),
        (0b_111_000_111_000_111_000, []),
        (0b_100_100_010_001_001_100, [0, 4, 7])
    ])
    def test_free_fields(self, marks, exp):
        board = Board(marks)
        assert sorted(list(board.free_fields())) == exp


class TestServer:
    """ Unit tests for the Server class.
    """
    

    _TESTFILE = os.path.join(os.path.realpath(os.path.dirname(__file__)),
            "test.db")


    def setup_method(self, method):
        clean_file(self._TESTFILE)
        db = SQLiteDatabase(filename=self._TESTFILE, clean=True)
        self._server = Server(db)


    def teardown_method(self, method):
        clean_file(self._TESTFILE)


    def test_register_player(self):
        name = random_string(MAX_NAME_LENGTH)
        pw_hash = random_hex_string(PW_HASH_LENGTH)
        response = self._server.register_player(name, pw_hash)
        assert response[Server.STATUS_KEY] == Server.STATUS_OK
        response = self._server.register_player(name, pw_hash)
        assert response[Server.STATUS_KEY] == Server.STATUS_ERROR


    def test_create_game_good(self):
        name1 = "dude1"
        pw_hash1 = random_hex_string(PW_HASH_LENGTH)
        self._server.register_player(name1, pw_hash1)
        name2 = "dude2"
        pw_hash2 = random_hex_string(PW_HASH_LENGTH)
        self._server.register_player(name2, pw_hash2)
        response = self._server.create_game(name1, pw_hash1, name2)
        assert response[Server.STATUS_KEY] == Server.STATUS_OK
        assert Server.GAME_ID_KEY in response


    def test_game_state(self):
        name1 = "dude1"
        pw_hash1 = random_hex_string(PW_HASH_LENGTH)
        self._server.register_player(name1, pw_hash1)
        name2 = "dude2"
        pw_hash2 = random_hex_string(PW_HASH_LENGTH)
        self._server.register_player(name2, pw_hash2)
        response = self._server.create_game(name1, pw_hash1, name2)
        game_id = response[Server.GAME_ID_KEY]
        response = self._server.game_state(name1, pw_hash1, game_id)
        assert response[Server.STATUS_KEY] == Server.STATUS_OK
        assert response[Server.TURN_KEY] == name1
        assert response[Server.BOARD_KEY] == 0


    def test_full_game(self):
        name1 = "carl"
        pw1 = random_hex_string(PW_HASH_LENGTH)
        name2 = "tom"
        pw2 = random_hex_string(PW_HASH_LENGTH)

        s = self._server
        r = s.register_player(name1, pw1)
        assert r[s.STATUS_KEY] == s.STATUS_OK
        r = s.register_player(name2, pw2)
        assert r[s.STATUS_KEY] == s.STATUS_OK
        r = s.create_game(name1, pw1, name2)
        assert r[s.STATUS_KEY] == s.STATUS_OK
        game_id = r[s.GAME_ID_KEY]
        
        # move 1 player 1
        r = s.make_turn(name1, pw1, 2, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # player 1 attempts to mark another field => error
        r = s.make_turn(name1, pw1, 3, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_ERROR

        # move 2 player 2
        # player 2 tries to write to an already marked field
        r = s.make_turn(name2, pw2, 2, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_ERROR
        # do the correct move
        r = s.make_turn(name2, pw2, 4, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # move 3 player 1
        r = s.make_turn(name1, pw1, 1, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # move 4 player 2
        r = s.make_turn(name2, pw2, 0, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # move 4 player 1
        r = s.make_turn(name1, pw1, 5, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # move 5 player 2 => win
        r = s.make_turn(name2, pw2, 8, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_OK

        # player 1 tries to set a field after game over
        r = s.make_turn(name1, pw1, 6, game_id)
        assert r[s.STATUS_KEY] == s.STATUS_ERROR

        # get the highscores
        r = s.highscore_list(3)
        assert r[s.STATUS_KEY] == s.STATUS_OK
        assert r[s.SCORES_KEY] == [
            {s.NAME_KEY: name2, s.SCORE_KEY: 1},
            {s.NAME_KEY: name1, s.SCORE_KEY: 0},
        ]
