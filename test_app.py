""" This module contains integration tests for the entire application.
"""

import os
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


    def test_highscore_empty(self):
        """ Checks that the highscore list can be obtained.
        """
        S = server.Server
        code, content = self.get("highscore/10")
        assert code == Status.OK.value
        assert content[S.STATUS_KEY] == S.STATUS_OK
        scores = content[S.SCORES_KEY]
        assert scores == []


    @pytest.mark.parametrize("name, pw", [
        # name too long
        ("a" * (MAX_NAME_LEN + 1), "1" * PW_LEN),
        # malformed pw (wrong size)
        ("a", "1" * (PW_LEN + 1)),
        # malformed pw (wrong characters)
        ("a", "x" * PW_LEN),
        # no name
        (None, "1" * PW_LEN),
        # no password
        ("a", None)
    ])
    def test_register_player_bad(self, name, pw):
        S = server.Server
        data = {}
        if name is not None:
            data["name"] = name
        if pw is not None:
            data["pw_hash"] = pw
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
