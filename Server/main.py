from fastapi import FastAPI, Depends, Body, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt, StrictFloat, ValidationError
from enum import Enum
from typing import Union, Optional

import sys, requests, json, sqlite3, secrets, binascii, hashlib, base64

MAX_LEADERBOARDS_PER_USER = 30
MAX_ENTRIES_PER_LEADERBOARD = 5000

MAX_NAME_LENGTH = 48
MAX_VALUE_BYTES = 4
MAX_ENTRIES_RETURNED_PER_REQUEST = 30


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(HTTPException)
async def error_exception_handler(request: Request, exc: HTTPException):
    print(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(str(exc))
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

def get_user_info(token: str):
    if token is None:
        return None
    if token.isalnum() == False:
        return None
    response = requests.get("https://itch.io/api/1/" + token + "/me")
    parsed = json.loads(response.text)
    return parsed.get("user")

def user_owns_leaderboard(user: int, leaderboard_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM leaderboard WHERE id == :leaderboard_id",
        {"leaderboard_id" : leaderboard_id})
    leaderboard = cur.fetchone()
    if leaderboard is None:
        return False
    return leaderboard["itch_user_id"] == user

def user_with_token_owns_leaderboard(token: str, leaderboard_id: int):
    userinfo = get_user_info(token)
    if userinfo is None:
        return False
    return user_owns_leaderboard(userinfo["id"], leaderboard_id)

def get_leaderboard_secret(leaderboard_id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM leaderboard WHERE id == :leaderboard_id",
        {"leaderboard_id" : leaderboard_id})
    leaderboard = cur.fetchone()
    if leaderboard is None:
        raise HTTPException(status_code=422, detail="There is no leaderboard with the id " + str(leaderboard_id))
    return leaderboard["secret"]
    
def get_leaderboard_sorting(leaderboard_id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM leaderboard WHERE id == :leaderboard_id",
        {"leaderboard_id" : leaderboard_id})
    leaderboard = cur.fetchone()
    if leaderboard is None:
        raise HTTPException(status_code=422, detail="There is no leaderboard with the id " + str(leaderboard_id))
    return leaderboard["sorting"]
    
def leaderboard_is_full(leaderboard_id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(1) AS count FROM entry WHERE leaderboard_id == :leaderboard_id",
        {"leaderboard_id" : leaderboard_id})
    count_table = cur.fetchone()
    return count_table["count"] >= MAX_ENTRIES_PER_LEADERBOARD
    
def has_maximum_number_of_leaderboards(itch_user_id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(1) AS count FROM leaderboard WHERE itch_user_id == :itch_user_id",
        {"itch_user_id" : itch_user_id})
    count_table = cur.fetchone()
    return count_table["count"] >= MAX_LEADERBOARDS_PER_USER


def get_connection():
    con = sqlite3.connect('./database/leaderboards.db')
    con.row_factory = sqlite3.Row
    return con

@app.post("/get_account_status")
def get_status_json(token: str = Body(..., embed=True)):
    return get_status_get(token)

@app.get("/get_account_status")
def get_status_get(token: str):
    userinfo = get_user_info(token)
    if userinfo is not None:
        return {"username":userinfo["username"], "id":userinfo["id"]}

@app.post("/get_leaderboards")
def get_leaderboards_json(token: str = Body(..., embed=True)):
    return get_leaderboards_get(token)

@app.get("/get_leaderboards")
def get_leaderboards_get(token: str):
    userinfo = get_user_info(token)
    if userinfo is not None:
        return get_leaderboards(userinfo["id"])

def get_leaderboards(itch_user_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute('SELECT * FROM leaderboard WHERE itch_user_id == :itch_user_id', {"itch_user_id" : itch_user_id})
    return (cur.fetchall())

class GetEntryCountParams(BaseModel):
    leaderboard_id: int

@app.post("/get_entry_count")
def get_entry_count_json(params: GetEntryCountParams):
    return get_entry_count(params.leaderboard_id)

@app.get("/get_entry_count")
def get_entry_count_get(leaderboard_id: int):
    return get_entry_count(leaderboard_id)

def get_entry_count(leaderboard_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM entry where leaderboard_id == :leaderboard_id", {"leaderboard_id" : leaderboard_id});
    return (cur.fetchone())

class GetEntriesParams(BaseModel):
    leaderboard_id: int
    start: int = 0
    count: int = 10
    search: str = ""

@app.post("/get_entries")
def get_entries_json(params: GetEntriesParams):
    return get_entries(params.leaderboard_id, params.start, params.count, params.search)

@app.get("/get_entries")
def get_entries_get(leaderboard_id: int, start: int = 0, count: int = 10, search: str = ""):
    return get_entries(leaderboard_id, start, count, search)

def get_entries(leaderboard_id: int, start: int = 0, count: int = 10, search: str = ""):
    if count > MAX_ENTRIES_RETURNED_PER_REQUEST:
        count = MAX_ENTRIES_RETURNED_PER_REQUEST
    sorting = get_leaderboard_sorting(leaderboard_id);
    position_query = {
        "a": "ROW_NUMBER () OVER ( ORDER BY value ASC ) position",
        "d": "ROW_NUMBER () OVER ( ORDER BY value DESC ) position",
        "n": "0 AS position"
    }
    con = get_connection()
    cur = con.cursor()
    scorequery = ("SELECT name, value, " + position_query[sorting] + " FROM"
        " entry WHERE leaderboard_id == :leaderboard_id")
    limitquery = " LIMIT :count OFFSET :start"
    if search != "":
        wholequery = "SELECT * FROM ( " + scorequery + " ) WHERE name LIKE :search" + limitquery
    else:
        wholequery = scorequery + limitquery
    start = start - 1
    cur.execute(wholequery, {"leaderboard_id" : leaderboard_id, "start" : start, "count" : count, "search" : search})
    return (cur.fetchall())

class CreateLeaderboardParams(BaseModel):
    name: str
    token: str

@app.post("/create_leaderboard")
def create_leaderboard_json(params: CreateLeaderboardParams):
    if len(params.name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail="Name is exceeding max length of " + str(MAX_NAME_LENGTH))
    userinfo = get_user_info(params.token)
    create_leaderboard(params.name, userinfo["id"])

def create_leaderboard(name: str, userid: int):
    if has_maximum_number_of_leaderboards(userid):
        raise HTTPException(status_code=422, detail="The maximum amount of leaderboards (" + str(MAX_LEADERBOARDS_PER_USER) + ") for this user has been reached")
    secret = secrets.token_hex(16)
    con = get_connection()
    cur = con.cursor()
    cur.execute(('INSERT INTO leaderboard(secret, itch_user_id, name)'
        ' VALUES(:secret, :userid, :name)'),
        {"secret" : secret, "userid" : userid, "name" : name})
    con.commit()

class SortingEnum(str, Enum):
    ascending = 'a'
    descending = 'd'
    none = 'n'

class SetLeaderboardSortingParams(BaseModel):
    id: int
    token: str
    sorting: SortingEnum

@app.post("/set_leaderboard_sorting")
def set_leaderboard_sorting_json(params: SetLeaderboardSortingParams):
    if user_with_token_owns_leaderboard(params.token, params.id):
        set_leaderboard_sorting(params.id, params.sorting)

def set_leaderboard_sorting(id: int, sorting: SortingEnum):
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE leaderboard SET sorting = :sorting WHERE id = :id;",
        {"id" : id, "sorting" : sorting})
    con.commit()
    
class SetLeaderboardNameParams(BaseModel):
    id: int
    token: str
    name: str

@app.post("/set_leaderboard_name")
def set_leaderboard_name_json(params: SetLeaderboardNameParams):
    if len(params.name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail="Name is exceeding max length of " + str(MAX_NAME_LENGTH))
    if user_with_token_owns_leaderboard(params.token, params.id):
        set_leaderboard_name(params.id, params.name)

def set_leaderboard_name(id: int, name: str):
    con = get_connection()
    cur = con.cursor()
    cur.execute("UPDATE leaderboard SET name = :name WHERE id = :id;",
        {"id" : id, "name": name})
    con.commit()

class DeleteLeaderboardParams(BaseModel):
    id: int
    token: str

@app.post("/delete_leaderboard")
def delete_leaderboard_json(params: DeleteLeaderboardParams):
    if params.token is not None:
        if user_with_token_owns_leaderboard(params.token, params.id):
            delete_leaderboard(params.id)

def delete_leaderboard(id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute('DELETE FROM leaderboard WHERE id = :id;', {"id" : id})
    con.commit()

class UpdateEntryParams(BaseModel):
    name: str
    value: Union[StrictInt, StrictFloat, float]
    leaderboard_id: int
    token: Union[str, None]

@app.post("/update_entry")
async def update_entry_json(request: Request):
    body = await request.body()
    ascii = body.decode('utf8')
    asciisplit = ascii.rsplit('}', 1)

    try:
        json_params = json.loads(asciisplit[0] + '}')
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=e.msg)
    
    try:
        params = UpdateEntryParams(**json_params)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    if len(params.name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail="Name is exceeding max length of " + str(MAX_NAME_LENGTH))
    
    max_int = pow(2, MAX_VALUE_BYTES * 8)//2-1
    if abs(params.value) > max_int:
        raise HTTPException(status_code=422, detail="Value is exceeding max size of +-" + str(max_int) + " (" + str(MAX_VALUE_BYTES) + " byte signed integer)")
    
    hash = asciisplit[1]

    if params.token is not None:
        if user_with_token_owns_leaderboard(params.token, params.leaderboard_id):
            update_entry(params.name, params.value, params.leaderboard_id)
            prune_table(params.leaderboard_id)
    else:
        if len(hash) == 0:
            raise HTTPException(status_code=422, detail="Hash is required when not using token")
        secret = get_leaderboard_secret(params.leaderboard_id)
        tohash = '/update_entry' + asciisplit[0] + '}' + secret
        hasher = hashlib.sha512()
        hasher.update(tohash.encode('utf-8'))
        needed_hash = hasher.digest()
        hasher = hashlib.sha256()
        hasher.update(tohash.encode('utf-8'))
        needed_hash2 = hasher.digest()
        if hash.lower() == needed_hash.hex().lower() or hash.lower() == needed_hash2.hex().lower():
            update_entry(params.name, params.value, params.leaderboard_id)
            prune_table(params.leaderboard_id)
        else:
            raise HTTPException(status_code=422, detail="Hash is not correct")
        
def update_entry(name: str, value: Union[int, float], leaderboard_id: int):
    sorting = get_leaderboard_sorting(leaderboard_id);
    override_mode = {
        "a": "<",
        "d": ">",
        "n": "<>"
    }
    con = get_connection()
    cur = con.cursor()
    cur.execute('INSERT INTO entry(name, value, leaderboard_id) VALUES(:name, :value, :leaderboard_id) ' +
        'ON CONFLICT(name, leaderboard_id) DO UPDATE SET value=excluded.value WHERE excluded.value ' + override_mode[sorting] + ' value;',
        {"name" : name, "value" : value, "leaderboard_id" : leaderboard_id})
    con.commit()

def prune_table(leaderboard_id: int):
    sorting = get_leaderboard_sorting(leaderboard_id);
    position_query = {
        "a": "ORDER BY value ASC",
        "d": "ORDER BY value DESC",
        "n": "ORDER BY ROWID DESC "
    }
    con = get_connection()
    cur = con.cursor()
    query = ('DELETE FROM entry WHERE leaderboard_id == :leaderboard_id ' +
        position_query[sorting] +
        ' LIMIT -1 OFFSET :MAX_ENTRIES_PER_LEADERBOARD;')
    cur.execute(query, {"leaderboard_id" : leaderboard_id, "MAX_ENTRIES_PER_LEADERBOARD" : MAX_ENTRIES_PER_LEADERBOARD})
    con.commit()

class DeleteEntryParams(BaseModel):
    name: str
    leaderboard_id: int
    token: str

@app.post("/delete_entry")
def delete_entry_json(params: DeleteEntryParams):
    if params.token is not None:
        if user_with_token_owns_leaderboard(params.token, params.leaderboard_id):
            delete_entry(params.name, params.leaderboard_id)

def delete_entry(name: str, leaderboard_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM entry WHERE leaderboard_id = :leaderboard_id AND name = :name;",
        {"leaderboard_id" : leaderboard_id, "name" : name})
    con.commit()

class ClearLeaderboardParams(BaseModel):
    leaderboard_id: int
    token: str

@app.post("/clear_leaderboard")
def clear_leaderboard_json(params: ClearLeaderboardParams):
    if params.token is not None:
        if user_with_token_owns_leaderboard(params.token, params.leaderboard_id):
            clear_leaderboard(params.leaderboard_id)

def clear_leaderboard(leaderboard_id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM entry WHERE leaderboard_id = :leaderboard_id;",
        {"leaderboard_id" : leaderboard_id})
    con.commit()
