""" This module contains integration tests for the entire application.
"""

import os
import itertools
from http import HTTPStatus as Status
from werkzeug.serving import make_server
import threading
import pytest
import requests as req
import server
import database
import json
import app

from tst_utils import random_string
from tst_utils import random_hex_string
from tst_utils import clean_file


HOST = "localhost"
PORT = 5000


class ServerThread(threading.Thread):
    """ Helper class to start and stop the webserver.
    """
    
    def __init__(self, app):
        threading.Thread.__init__(self)
        self._server = make_server(HOST, PORT, app)


    def run(self):
        self._server.serve_forever()


    def kill(self):
        self._do = False
        self._server.shutdown()


MAX_NAME_LEN = database.MAX_NAME_LENGTH
PW_LEN = database.PW_HASH_LENGTH


class TestApp:
    """ Integration tests for the entire applicatiom.

        The tests defined in this class start the server and communicate with
        it using actual HTTP requests.

        Every test works like this:

            1) Start the webserver using an empty database.
            2) Communicate to the server via HTTP requests, just as a game
               client would do.
            3) Verify the results.
            4) Cleanup.
    """
    
    _server = None
    _TESTFILE = os.path.join(os.path.realpath(os.path.dirname(__file__)),
            "test.db")


    def setup_method(self, method):
        clean_file(self._TESTFILE)
        db = database.SQLiteDatabase(filename=self._TESTFILE, clean=True,
                check_same_thread=False)
        app.serv = server.Server(db)
        self._server = ServerThread(app.flask_app)
        self._server.start()


    def teardown_method(self, method):
        self._server.kill()
        self._server = None
        clean_file(self._TESTFILE)


    @staticmethod
    def get(suffix):
        url = f"http://{HOST}:{PORT}/{suffix}"
        res = req.get(url)
        code = res.status_code
        content = json.loads(res.content.decode())
        return code, content


    @staticmethod
    def post(suffix, data=None):
        url = f"http://{HOST}:{PORT}/{suffix}"
        data = {} if data is None else data
        res = req.post(url, data=data)
        code = res.status_code
        content = json.loads(res.content.decode())
        return code, content


    @staticmethod
    def bogus_names():
        return (None, "", "a" * (MAX_NAME_LEN + 1))



    @staticmethod
    def bogus_pw_hashes():
        return (None, "", "1" * (PW_LEN + 1), "foobar")


    def test_highscore_empty(self):
        """ Checks that the highscore list can be obtained.
        """
        S = server.Server
        code, content = self.get("highscore/10")
        assert code == Status.OK.value
        assert content[S.STATUS_KEY] == S.STATUS_OK
        scores = content[S.SCORES_KEY]
        assert scores == []


    def test_register_player_bad(self):
        """ Tests that post parameters to register_player are properly
            checked.
        """
        S = server.Server
        bad_names = self.bogus_names()
        bad_pws = self.bogus_pw_hashes()
        for name, pw_hash in itertools.product(bad_names, bad_pws):
            data = {}
            if name is not None:
                data["name"] = name
            if pw_hash is not None:
                data["pw_hash"] = pw_hash
            code, content = self.post("register_player", data)
            assert code == Status.BAD_REQUEST.value
            assert content[S.STATUS_KEY] == S.STATUS_ERROR
 

    def test_register_player_good(self):
        S = server.Server
        name = random_string(database.MAX_NAME_LENGTH)
        pw_hash = random_hex_string(database.PW_HASH_LENGTH)
        data = {"name": name, "pw_hash": pw_hash}
        code, content = self.post("register_player", data)
        assert code == Status.OK.value
        assert content[S.STATUS_KEY] == S.STATUS_OK
        # adding the same guy again will fail, though ...
        code, content = self.post("register_player", data)
        assert code == Status.BAD_REQUEST.value
        assert content[S.STATUS_KEY] == S.STATUS_ERROR
        # adding a different guy should work
        name2 = name
        while name2 == name:
            name2 = random_string(database.MAX_NAME_LENGTH)
        pw_hash = random_hex_string(database.PW_HASH_LENGTH)
        data = {"name": name2, "pw_hash": pw_hash}
        code, content = self.post("register_player", data)
        assert code == Status.OK.value
        assert content[S.STATUS_KEY] == S.STATUS_OK
        # verify that the players made it into the database ...
        code, content = self.get("highscore/10")
        assert code == Status.OK.value
        scores = content[S.SCORES_KEY]
        assert len(scores) == 2
        names = set(s[S.NAME_KEY] for s in scores)
        assert names == set([name, name2])


    def test_create_game_bad(self):
        """ Tests that parameters to create_game are sanity-checked.
        """
        S = server.Server
        tests = itertools.product(self.bogus_names(), self.bogus_pw_hashes(),
                self.bogus_names())
        for p1_name, pw_hash, p2_name in tests:
            data = {}
            if p1_name is not None:
                data["player_1_name"] = p1_name
            if pw_hash is not None:
                data["pw_hash"] = pw_hash
            if p1_name is not None:
                data["player_2_name"] = p2_name
            code, content = self.post("create_game", data)
            assert code == Status.BAD_REQUEST.value
            assert content[S.STATUS_KEY] == S.STATUS_ERROR


    def test_create_game_good(self):
        """ Tests that a game can be created if parameters are correct.
        """
        S = server.Server
        # add some players
        name1 = "tom"
        pw_hash1 = "1" * PW_LEN
        name2 = "hank"
        pw_hash2 = "2" * PW_LEN
        code, _ = self.post("register_player",
                {"name": name1, "pw_hash": pw_hash1})
        assert code == Status.OK.value
        code, _ = self.post("register_player",
                {"name": name2, "pw_hash": pw_hash2})
        assert code == Status.OK.value
        # create the game
        data = {
            "player_1_name": name1,
            "player_2_name": name2,
            "pw_hash"      : pw_hash1
        }
        code, content = self.post("create_game", data)
        assert code == Status.OK.value
        assert content[S.STATUS_KEY] == S.STATUS_OK
        assert content[S.GAME_ID_KEY] == 1


    def test_game_state_bad(self):
        pass
