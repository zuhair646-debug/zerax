from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

app = FastAPI(title="App Backend")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

USERS = {}
ITEMS = {}

class UserIn(BaseModel):
    email: str
    name: str = ""

class ItemIn(BaseModel):
    title: str
    body: str = ""

@app.get("/api/health")
def health():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.post("/api/users")
def create_user(u: UserIn):
    uid = uuid.uuid4().hex
    USERS[uid] = {"id": uid, **u.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}
    return USERS[uid]

@app.get("/api/users")
def list_users():
    return list(USERS.values())

@app.post("/api/items")
def create_item(it: ItemIn):
    iid = uuid.uuid4().hex
    ITEMS[iid] = {"id": iid, **it.model_dump(), "created_at": datetime.now(timezone.utc).isoformat()}
    return ITEMS[iid]

@app.get("/api/items")
def list_items():
    return list(ITEMS.values())
