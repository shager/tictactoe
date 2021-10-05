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
#serv = server.Server(database.SQLiteDatabase())
serv = None


_PW_REGEX = re.compile("^[0-9a-f]{" + str(database.PW_HASH_LENGTH) + "}$")
_MIME = "application/json"


def code_from_response(response: server.Response) -> int:
    S = server.Server
    if response[S.STATUS_KEY] == S.STATUS_OK:
        return Status.OK.value
    return Status.BAD_REQUEST.value


def _check_name(name: str) -> None:
    """ Raises a ValueError if the name is malformed.

        - name: the name to check
    """
    if len(name) > database.MAX_NAME_LENGTH:
        resp = json.dumps(serv.error_msg("name too long"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))


def _check_pw_hash(pw_hash: str) -> None:
    """ Raises a ValueError if the password hash is malformed.

        - pw_hash: the password hash to check
    """
    if _PW_REGEX.match(pw_hash) is None:
        resp = json.dumps(serv.error_msg("invalid pw hash"))
        raise ValueError(Response(response=resp,
                status=Status.BAD_REQUEST.value, mimetype=_MIME))


@flask_app.route("/highscore/<int:max_entries>", methods=["GET"])
def highscore(max_entries: int) -> Response:
    highscore_list = serv.highscore_list(max_entries)
    return Response(response=json.dumps(highscore_list),
            status=Status.OK.value, mimetype=_MIME)


@flask_app.route("/register_player", methods=["POST"])
def register_player() -> Response:
    name = str(request.values.get("name"))
    pw_hash = str(request.values.get("pw_hash")).lower()
    try:
        _check_name(name)
        _check_pw_hash(pw_hash)
    except ValueError as error:
        return error.args[0]
    response = serv.register_player(name, pw_hash)
    code = code_from_response(response)
    return Response(response=json.dumps(response), status=code, mimetype=_MIME)


@flask_app.route("/create_game", methods=["POST"])
def create_game() -> str:
    player_1_name = str(request.values("player_1_name"))
    pw_hash = str(request.values.get("pw_hash")).lower()
    player_2_name = str(request.values("player_2_name"))
    if len(player_1_name) > database.MAX_NAME_LENGTH:
        abort(400)
    if len(player_2_name) > database.MAX_NAME_LENGTH:
        abort(400)
    if _PW_REGEX.match(pw_hash) is None:
        abort(400)
    response = serv.create_game(player_1_name, pw_hash, player_2_name)
    return json.dumps(response)


def _main():
    global serv
    serv = server.Server(database.SQLiteDatabase())
    flask_app.run(debug=True, threaded=False, processes=1)


if __name__ == "__main__":
    _main()
