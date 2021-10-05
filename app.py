#!/usr/bin/env python3

import sys
import json
import re
from typing import Optional
from http import HTTPStatus as Status
from flask import Flask
from flask import request
from flask import abort
from flask import Response
import server
import database



flask_app = Flask(__name__)
serv = None


_PW_REGEX = re.compile("^[0-9a-f]{" + str(database.PW_HASH_LENGTH) + "}$")
_MIME = "application/json"


# **************************** helper functions ***************************** #


def code_from_response(response: server.Response) -> int:
    S = server.Server
    if response[S.STATUS_KEY] == S.STATUS_OK:
        return Status.OK.value
    return Status.FORBIDDEN.value


def _check_name(name_key: str) -> str:
    """ Raises a ValueError if the user name is malformed.
        Returns the username if all is nice.

        - name: the name to check
    """
    name = request.values.get(name_key)
    if name is None:
        resp = json.dumps(serv.error_msg(f"no {name_key}"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))
    name = str(name)
    if len(name) == 0 or len(name) > database.MAX_NAME_LENGTH:
        resp = json.dumps(serv.error_msg("name too long"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))
    return name


def _check_pw_hash(pw_hash_key: str) -> str:
    """ Raises a ValueError if the password hash is malformed.

        - pw_hash: the password hash to check
    """
    pw_hash = request.values.get(pw_hash_key)
    if pw_hash is None:
        resp = json.dumps(serv.error_msg(f"no {pw_hash_key}"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))
    pw_hash = str(pw_hash).lower()
    if _PW_REGEX.match(pw_hash) is None:
        resp = json.dumps(serv.error_msg("invalid pw hash"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))
    return pw_hash


def _raise_bad_request(why: str) -> None:
    """ Raises a ValueError with a Response object.
    """
    resp = json.dumps(serv.error_msg(why))
    raise ValueError(Response(response=resp,
            status=Status.BAD_REQUEST.value, mimetype=_MIME))


def _check_game_id(key: str) -> int:
    """ Raises a ValueError if the password hash is malformed.
        Returns a valid ID in case of success.

        - key: the parameter name for the game id
    """
    game_id = request.values.get(key)
    if game_id is None:
        _raise_bad_request(f"no {key}")
    try:
        game_id = int(game_id)
    except ValueError:
        _raise_bad_request(f"invalid {key} (no integer)")
    if game_id <= 0:
        _raise_bad_request(f"invalid {key} (non-positive)")
    return game_id


# ****************  below are the implemented HTTP requests ***************** #


# parameter names
PARAM_NAME         = "name"
PARAM_PLAYER1_NAME = "player_1_name"
PARAM_PLAYER2_NAME = "player_2_name"
PARAM_PW_HASH      = "pw_hash"
PARAM_GAME_ID      = "game_id"


@flask_app.route("/highscore/<int:max_entries>", methods=["GET"])
def highscore(max_entries: int) -> Response:
    highscore_list = serv.highscore_list(max_entries)
    return Response(response=json.dumps(highscore_list),
            status=Status.OK.value, mimetype=_MIME)


@flask_app.route("/register_player", methods=["POST"])
def register_player() -> Response:
    try:
        name = _check_name(PARAM_NAME)
        pw_hash = _check_pw_hash(PARAM_PW_HASH)
    except ValueError as error:
        return error.args[0]
    response = serv.register_player(name, pw_hash)
    code = code_from_response(response)
    return Response(response=json.dumps(response), status=code, mimetype=_MIME)


@flask_app.route("/create_game", methods=["POST"])
def create_game() -> Response:
    try:
        player_1_name = _check_name(PARAM_PLAYER1_NAME)
        player_2_name = _check_name(PARAM_PLAYER2_NAME)
        pw_hash = _check_pw_hash(PARAM_PW_HASH)
    except ValueError as error:
        return error.args[0]
    response = serv.create_game(player_1_name, pw_hash, player_2_name)
    code = code_from_response(response)
    return Response(response=json.dumps(response), status=code, mimetype=_MIME)


# XXX: not sure whether to use GET for this
# Technically, this operation is idempotent and doesn't change anything.
# However, transfering a PW hash in the URL is also not great.
# Therefore, we put in the body => but this may go against the idea of GET ...
@flask_app.route("/game_state", methods=["GET"])
def game_state() -> Response:
    try:
        name = _check_name(PARAM_NAME)
        pw_hash = _check_pw_hash(PARAM_PW_HASH)
        game_id = _check_game_id(PARAM_GAME_ID)
    except ValueError as error:
        return error.args[0]
    response = serv.game_state(name, pw_hash, game_id)
    code = code_from_response(response)
    return Response(response=json.dumps(response), status=code, mimetype=_MIME)


def _main():
    global serv
    serv = server.Server(database.SQLiteDatabase())
    flask_app.run(debug=True, threaded=False, processes=1)


if __name__ == "__main__":
    _main()
