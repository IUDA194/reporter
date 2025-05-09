# tests/test_api.py
import json
import uuid
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.database as db_module
from app.routers.sockets import active_connections
from app.auth import get_user_from_jwt

@pytest.fixture(autouse=True)
def clear_active_ws():
    # Перед каждым тестом чистим активные сокеты
    active_connections.clear()
    yield
    active_connections.clear()

@pytest.fixture
def client(monkeypatch):
    # --- «redis» в памяти ---
    fake_store = {}
    class FakeRedis:
        def set(self, key, val, ex=None):
            fake_store[key] = val
        def delete(self, key):
            fake_store.pop(key, None)
        def get(self, key):
            return fake_store.get(key)
    monkeypatch.setattr(db_module, 'redis', FakeRedis())

    # --- «users_collection» для /confirm-code ---
    class FakeUsersColl:
        async def find_one(self, q):
            return None  # всегда создаём нового
        async def insert_one(self, data):
            class R: inserted_id = uuid.uuid4()
            return R()
    monkeypatch.setattr(db_module, 'users_collection', FakeUsersColl())

    # --- «collection» для /tasks/submit и /tasks/reports ---
    class FakeTasksColl:
        def __init__(self):
            self.data = []
        async def insert_one(self, doc):
            class R: inserted_id = "fakeid"
            return R()
        def find(self, q):
            class C:
                def __init__(self, data): self._data = data
                async def to_list(self, length):
                    return self._data
            return C(self.data)
    fake_tasks = FakeTasksColl()
    monkeypatch.setattr(db_module, 'collection', fake_tasks)

    # --- оверрайдим JWT-депенденси, чтобы всегда «логинить» одного и того же пользователя ---
    async def fake_user(token: str = None):
        return {
            "user_id": "507f1f77bcf86cd799439011",
            "chat_id": "123",
            "username": "johndoe",
            "full_name": "John Doe"
        }
    app.dependency_overrides[get_user_from_jwt] = fake_user

    yield TestClient(app)

    # сбросим оверрайды
    app.dependency_overrides.clear()


def test_websocket_login_and_jwt(client):
    # Подключаемся по WS
    with client.websocket_connect("/ws/login?referred_by=testref") as ws:
        # 1) получаем { uuid, bot_url }
        raw = ws.receive_text()
        data = json.loads(raw)
        assert "uuid" in data and isinstance(data["uuid"], str)
        assert "bot_url" in data and data["bot_url"].startswith("http")
        uid = data["uuid"]
        # WS внутри active_connections
        assert uid in active_connections

        # 2) шлём не-JSON → получаем ошибку
        ws.send_text("not json")
        err = json.loads(ws.receive_text())
        assert err["error"] == "Invalid JSON"

        # 3) шлём JSON без jwt → другая ошибка
        ws.send_text(json.dumps({"foo":"bar"}))
        err2 = json.loads(ws.receive_text())
        assert err2["error"] == "JWT not found"

        # 4) шлём JSON c jwt → получаем status=jwt_saved
        ws.send_text(json.dumps({"jwt":"token123"}))
        ok = json.loads(ws.receive_text())
        assert ok["status"] == "jwt_saved"


def test_confirm_code_success_and_errors(client):
    # Подставим «сокет» вручную
    class StubWS:
        def __init__(self): self.sent = []
        async def send_text(self, txt): self.sent.append(txt)

    stub = StubWS()
    uid = str(uuid.uuid4())
    active_connections[uid] = stub

    # — коррекный запрос
    payload = {
        "uuid": uid,
        "chat_id": "321",
        "username": "user1",
        "full_name": "User One",
        "referred_by": "ref1"
    }
    resp = client.post("/service/confirm-code", json=payload)
    assert resp.status_code == 200
    j = resp.json()
    assert j["status"] == "sent" and "token" in j

    # ws.send_text вызван с access_token
    sent = json.loads(stub.sent[0])
    assert sent["status"] == "success" and "access_token" in sent

    # — без uuid → 400
    r2 = client.post("/service/confirm-code", json={"chat_id":"321"})
    assert r2.status_code == 400
    assert "error" in r2.json()

    # — без chat_id → 400
    r3 = client.post("/service/confirm-code", json={"uuid":uid})
    assert r3.status_code == 400
    assert "error" in r3.json()


def test_submit_and_get_reports(client):
    # 1) Submit
    report = {
        "date": "2025-05-08",
        "developer": "alice",
        "yesterday": ["t1"],
        "today": ["t2"],
        "blockers": []
    }
    headers = {"Authorization": "Bearer faketoken"}
    r1 = client.post("/tasks/submit", json=report, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["inserted_id"] == "fakeid"

    # Подготовим «найденные» данные
    # (наш fake_tasks = db_module.collection)
    fake_tasks = db_module.collection
    fake_tasks.data.append({
        "_id": "fakeid",
        "user_id": "507f1f77bcf86cd799439011",
        "date": "2025-05-08",
        "developer": "alice",
        "yesterday": [],
        "today": [],
        "blockers": [],
        "created_at": datetime.utcnow()
    })

    # 2) GET /tasks/reports?date=2025-05-08
    r2 = client.get("/tasks/reports?date=2025-05-08", headers=headers)
    assert r2.status_code == 200
    arr = r2.json()
    assert isinstance(arr, list)
    assert arr and arr[0]["date"] == "2025-05-08"

    # 3) GET /tasks/reports без date и с некорректным owner_id
    r3 = client.get("/tasks/reports", headers=headers)
    assert r3.status_code == 200  # просто вернёт всё по текущему user_id

    r4 = client.get("/tasks/reports?owner_id=invalid!", headers=headers)
    assert r4.status_code == 400
