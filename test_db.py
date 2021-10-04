import os
import random
from database import SQLiteDatabase
from database import MAX_NAME_LENGTH
from database import PW_HASH_LENGTH

from tst_utils import random_string
from tst_utils import random_hex_string
from tst_utils import clean_file


class TestDatabase:

    _TESTFILE = os.path.join(os.path.realpath(os.path.dirname(__file__)),
            "test.db")


    def setup_method(self, method):
        clean_file(self._TESTFILE)
        self._db = SQLiteDatabase(filename=self._TESTFILE, clean=True)


    def teardown_method(self, method):
        clean_file(self._TESTFILE)


    def test_register_player(self):
        name = random_string(MAX_NAME_LENGTH)
        assert self._db.player_by_name(name) is None
        pw_hash = random_hex_string(PW_HASH_LENGTH)
        self._db.register_player(name, pw_hash)
        player = self._db.player_by_name(name)
        assert player.name == name
        assert player.hash == pw_hash


    def test_highscore_simple(self):
        max_entries = random.randrange(3, 5)
        assert len(list(self._db.highscore(max_entries))) == 0
        for i in range(10):
            name = f"dude{i}"
            pw_hash = random_hex_string(PW_HASH_LENGTH)
            self._db.register_player(name, pw_hash)
        entries = list(self._db.highscore(max_entries))
        assert len(entries) == max_entries
        for entry in entries:
            assert entry.name.startswith("dude")
            assert entry.score == 0
