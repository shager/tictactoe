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


def code_from_response(response: server.Response) -> int:
    S = server.Server
    if response[S.STATUS_KEY] == S.STATUS_OK:
        return Status.OK.value
    return Status.BAD_REQUEST.value


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


# below are the implemented HTTP requests


@flask_app.route("/highscore/<int:max_entries>", methods=["GET"])
def highscore(max_entries: int) -> Response:
    highscore_list = serv.highscore_list(max_entries)
    return Response(response=json.dumps(highscore_list),
            status=Status.OK.value, mimetype=_MIME)


@flask_app.route("/register_player", methods=["POST"])
def register_player() -> Response:
    try:
        name = _check_name("name")
        pw_hash = _check_pw_hash("pw_hash")
    except ValueError as error:
        return error.args[0]
    response = serv.register_player(name, pw_hash)
    code = code_from_response(response)
    return Response(response=json.dumps(response), status=code, mimetype=_MIME)


@flask_app.route("/create_game", methods=["POST"])
def create_game() -> Response:
    try:
        player_1_name = _check_name("player_1_name")
        player_2_name = _check_name("player_2_name")
        pw_hash = _check_pw_hash("pw_hash")
    except ValueError as error:
        return error.args[0]
    response = serv.create_game(player_1_name, pw_hash, player_2_name)
    return json.dumps(response)


def _main():
    global serv
    serv = server.Server(database.SQLiteDatabase())
    flask_app.run(debug=True, threaded=False, processes=1)


if __name__ == "__main__":
    _main()
