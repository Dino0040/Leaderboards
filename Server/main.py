from fastapi import FastAPI, Depends, Body, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, StrictInt, StrictFloat, ValidationError
from typing import Union
import sys

import requests, json, sqlite3, random, binascii, hashlib, base64

MAX_LEADERBOARDS_PER_USER = 30
MAX_ENTRIES_PER_LEADERBOARD = 5000

MAX_NAME_LENGTH = 30
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
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

def get_user_info(token: str):
    if token is not None:
        response = requests.get("https://itch.io/api/1/" + token + "/me")
        parsed = json.loads(response.text)
        return parsed.get("user")
    return None

def user_owns_leaderboard(user: int, id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM leaderboard WHERE id == :id",
        {"id" : id})
    leaderboard = cur.fetchone()
    return leaderboard["owner"] == user

def user_with_token_owns_leaderboard(token: str, id: int):
    userinfo = get_user_info(token)
    return user_owns_leaderboard(userinfo["id"], id)

def get_leaderboard_secret(id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT * FROM leaderboard WHERE id == :id",
        {"id" : id})
    leaderboard = cur.fetchone()
    return leaderboard["secret"]
    
def leaderboard_is_full(id : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(1) AS count FROM entry WHERE leaderboard == :id",
        {"id" : id})
    count_table = cur.fetchone()
    return count_table["count"] >= MAX_ENTRIES_PER_LEADERBOARD
    
def has_maximum_number_of_leaderboards(owner : int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT COUNT(1) AS count FROM leaderboard WHERE owner == :owner",
        {"owner" : owner})
    count_table = cur.fetchone()
    return count_table["count"] >= MAX_LEADERBOARDS_PER_USER


def get_connection():
    con = sqlite3.connect('./database/leaderboards.db')
    con.row_factory = sqlite3.Row
    return con

@app.post("/getstatus")
def get_status_json(token: str = Body(..., embed=True)):
    return get_status_get(token)

@app.get("/getstatus")
def get_status_get(token: str):
    userinfo = get_user_info(token)
    if userinfo is not None:
        return {"username":userinfo["username"], "id":userinfo["id"]}

@app.post("/getleaderboards")
def get_leaderboards_json(token: str = Body(..., embed=True)):
    return get_leaderboards_get(token)

@app.get("/getleaderboards")
def get_leaderboards_get(token: str):
    userinfo = get_user_info(token)
    if userinfo is not None:
        return get_leaderboards(userinfo["id"])

def get_leaderboards(owner: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute('SELECT * FROM leaderboard WHERE owner == :owner', {"owner" : owner})
    return (cur.fetchall())

class GetScoreEntriesParams(BaseModel):
    id: int
    start: int = 0
    count: int = 10
    search: str = ""

@app.post("/getscoreentries")
def get_score_entries_json(params: GetScoreEntriesParams):
    return get_score_entries(params.id, params.start, params.count, params.search)

@app.get("/getscoreentries")
def get_score_entries_get(id: int, start: int = 0, count: int = 10, search: str = ""):
    return get_score_entries(id, start, count, search)

def get_score_entries(id: int, start: int = 0, count: int = 10, search: str = ""):
    if count > MAX_ENTRIES_RETURNED_PER_REQUEST:
        count = MAX_ENTRIES_RETURNED_PER_REQUEST
    con = get_connection()
    cur = con.cursor()
    scorequery = ("SELECT name, value, ROW_NUMBER ()"
        " OVER ( ORDER BY value DESC ) position FROM"
        " entry WHERE leaderboard == :id")
    limitquery = " LIMIT :count OFFSET :start"
    if search != "":
        wholequery = "SELECT * FROM ( " + scorequery + " ) WHERE name LIKE :search" + limitquery
    else:
        wholequery = scorequery + limitquery
    start = start - 1
    cur.execute(wholequery, {"id" : id, "start" : start, "count" : count, "search" : search})
    return (cur.fetchall())

class CreateLeaderboardParams(BaseModel):
    name: str
    token: str

@app.post("/createleaderboard")
def create_leaderboard_json(params: CreateLeaderboardParams):
    create_leaderboard_get(params.name, params.token)

def create_leaderboard_get(name: str, token : str):
    if token is not None:
        userinfo = get_user_info(token)
        create_leaderboard(name, userinfo["id"])

def create_leaderboard(name: str, userid: int):
    if has_maximum_number_of_leaderboards(userid):
        raise HTTPException(status_code=422, detail="The maximum amount of leaderboards (" + str(MAX_LEADERBOARDS_PER_USER) + ") for this user has been reached")
    secret = '%x' % random.getrandbits(128)
    con = get_connection()
    cur = con.cursor()
    cur.execute(('INSERT INTO leaderboard(secret, owner, name)'
        ' VALUES(:secret, :userid, :name)'),
        {"secret" : secret, "userid" : userid, "name" : name})
    con.commit()

class DeleteLeaderboardParams(BaseModel):
    id: int
    token: str

@app.post("/deleteleaderboard")
def delete_leaderboard_json(params: DeleteLeaderboardParams):
    delete_leaderboard_get(params.id, params.token)

def delete_leaderboard_get(id: int, token : str):
    if token is not None:
        if user_with_token_owns_leaderboard(token, id):
            delete_leaderboard(id)

def delete_leaderboard(id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute('DELETE FROM leaderboard WHERE id = :id;', {"id" : id})
    con.commit()

class SubmitScoreEntryParams(BaseModel):
    name: str
    value: Union[StrictInt, StrictFloat, float]
    id: int
    token: Union[str, None]

@app.post("/submitscoreentry")
async def submit_score_entry_json(request: Request):
    body = await request.body()
    ascii = body.decode('ASCII')
    asciisplit = ascii.rsplit('}', 1)

    try:
        json_params = json.loads(asciisplit[0] + '}')
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=e.msg)
    
    try:
        params = SubmitScoreEntryParams(**json_params)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    if len(params.name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail="Name is exceeding max length of " + str(MAX_NAME_LENGTH))
    
    max_int = pow(2, MAX_VALUE_BYTES * 8)//2-1
    if abs(params.value) > max_int:
        raise HTTPException(status_code=422, detail="Value is exceeding max size of +-" + str(max_int) + " (" + str(MAX_VALUE_BYTES) + " byte signed integer)")
    
    # This will need to be changed later on to delete the lower scores instead of blocking new ones
    if leaderboard_is_full(params.id):
        raise HTTPException(status_code=422, detail="The leaderboard has reached the maximum size of " + str(MAX_ENTRIES_PER_LEADERBOARD))
    
    hash = asciisplit[1]

    if params.token is not None:
        if user_with_token_owns_leaderboard(params.token, params.id):
            submit_score_entry(params.name, params.value, params.id)
    else:
        if len(hash) == 0:
            raise HTTPException(status_code=422, detail="Hash is required when not using token")
        secret = get_leaderboard_secret(params.id)
        tohash = '/submitscoreentry' + asciisplit[0] + '}' + secret
        hasher = hashlib.sha512()
        hasher.update(tohash.encode('utf-8'))
        needed_hash = hasher.digest()
        hasher = hashlib.sha256()
        hasher.update(tohash.encode('utf-8'))
        needed_hash2 = hasher.digest()
        if hash.lower() == needed_hash.hex().lower() or hash.lower() == needed_hash2.hex().lower():
            submit_score_entry(params.name, params.value, params.id)
        else:
            raise HTTPException(status_code=422, detail="Hash is not correct")
        
def submit_score_entry(name: str, value: Union[int, float], id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute('INSERT INTO entry(name, value, leaderboard) VALUES(:name, :value, :id) ' +
        'ON CONFLICT(name, leaderboard) DO UPDATE SET value=excluded.value WHERE excluded.value>value;',
        {"name" : name, "value" : value, "id" : id})
    con.commit()

class DeleteScoreEntryParams(BaseModel):
    name: str
    id: int
    token: str

@app.post("/deletescoreentry")
def delete_score_entry_json(params: DeleteScoreEntryParams):
    delete_score_entry_get(params.name, params.id, params.token)

def delete_score_entry_get(name: str, id: int, token : str):
    if token is not None:
        if user_with_token_owns_leaderboard(token, id):
            delete_score_entry(name, id)

def delete_score_entry(name: str, id: int):
    con = get_connection()
    cur = con.cursor()
    cur.execute("DELETE FROM entry WHERE leaderboard = :id AND name = :name;",
        {"id" : id, "name" : name})
    con.commit()
