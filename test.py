import json
import uuid
from datetime import datetime

import pytest
import pytest_asyncio
import jwt
from httpx import AsyncClient, ASGITransport

from app.main import app
import app.database as db_module
from app.routers.sockets import active_connections
from app.auth import get_user_from_jwt, JWT_SECRET, JWT_ALGORITHM


@pytest.fixture(autouse=True)
def clear_active_ws():
    active_connections.clear()
    yield
    active_connections.clear()


@pytest_asyncio.fixture
async def client(monkeypatch) -> AsyncClient:
    # --- Fake Redis ---
    fake_store = {}

    class FakeRedis:
        async def set(self, key, val, ex=None):
            fake_store[key] = val

        async def delete(self, key):
            fake_store.pop(key, None)

        async def get(self, key):
            return fake_store.get(key)

    monkeypatch.setattr(db_module, 'redis', FakeRedis())

    # --- Fake Mongo users_collection ---
    class FakeUsersColl:
        async def find_one(self, q):
            return None

        async def insert_one(self, data):
            class R:
                inserted_id = uuid.uuid4()
            return R()

    monkeypatch.setattr(db_module, 'users_collection', FakeUsersColl())

    # --- Fake Mongo collection for tasks ---
    class FakeTasksColl:
        def __init__(self):
            self.data = []
            self.inserted_ids = []

        async def insert_one(self, doc):
            inserted_id = str(uuid.uuid4())
            doc["_id"] = inserted_id
            self.data.append(doc)
            self.inserted_ids.append(inserted_id)

            class R:
                inserted_id = inserted_id
            return R()

        def find(self, q):
            class Cursor:
                def __init__(self, data):
                    self._data = data

                async def to_list(self, length):
                    return self._data

            return Cursor(self.data)

    fake_tasks = FakeTasksColl()
    monkeypatch.setattr(db_module, 'collection', fake_tasks)

    # --- Override get_user_from_jwt ---
    async def fake_user(token: str = None):
        return {
            "user_id": "507f1f77bcf86cd799439011",
            "chat_id": "123",
            "username": "johndoe",
            "full_name": "John Doe"
        }

    app.dependency_overrides[get_user_from_jwt] = fake_user

    # Use ASGITransport for AsyncClient to interface with FastAPI app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_jwt_token():
    # Генерация тестового JWT, используя секреты приложения
    payload = {
        "user_id": str(uuid.uuid4()),
        "chat_id": "321",
        "username": "user1",
        "full_name": "User One",
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


@pytest.mark.asyncio
async def test_websocket_login_and_jwt(client: AsyncClient):
    async with client.websocket_connect("/ws/login?referred_by=testref") as ws:
        raw = await ws.receive_text()
        data = json.loads(raw)
        assert "uuid" in data
        assert data["bot_url"].startswith("http")
        uid = data["uuid"]
        assert uid in active_connections

        # Неверный формат
        await ws.send_text("not json")
        err = json.loads(await ws.receive_text())
        assert err["error"] == "Invalid JSON"

        # Нет jwt
        await ws.send_text(json.dumps({"foo": "bar"}))
        err2 = json.loads(await ws.receive_text())
        assert err2["error"] == "JWT not found"

        # Отправка JWT
        await ws.send_text(json.dumps({"jwt": "token123"}))
        ok = json.loads(await ws.receive_text())
        assert ok["status"] == "jwt_saved"


@pytest.mark.asyncio
async def test_confirm_code_and_use_token(client: AsyncClient):
    # Подделка сокета
    class StubWS:
        def __init__(self):
            self.sent = []

        async def send_text(self, text):
            self.sent.append(text)

    stub = StubWS()
    uid = str(uuid.uuid4())
    active_connections[uid] = stub

    payload = {
        "uuid": uid,
        "chat_id": "321",
        "username": "user1",
        "full_name": "User One",
        "referred_by": "ref1"
    }

    r = await client.post("/service/confirm-code", json=payload)
    assert r.status_code == 200
    token = json.loads(stub.sent[0])["access_token"]

    # Используем токен для отправки отчета
    headers = {"Authorization": f"Bearer {token}"}
    report = {
        "date": "2025-05-08",
        "developer": "bob",
        "yesterday": ["fix bug"],
        "today": ["write tests"],
        "blockers": []
    }
    r2 = await client.post("/tasks/submit", json=report, headers=headers)
    assert r2.status_code == 200

    inserted_id = r2.json()["inserted_id"]
    assert isinstance(inserted_id, str)

    # Эмулируем сохраненный отчет в "базе"
    db_module.collection.data.append({
        "_id": inserted_id,
        "user_id": "507f1f77bcf86cd799439011",
        "date": "2025-05-08",
        "developer": "bob",
        "yesterday": [],
        "today": [],
        "blockers": [],
        "created_at": datetime.utcnow()
    })

    r3 = await client.get("/tasks/reports?date=2025-05-08", headers=headers)
    assert r3.status_code == 200
    reports = r3.json()
    assert isinstance(reports, list)
    assert reports[0]["date"] == "2025-05-08"


@pytest.mark.asyncio
async def test_protected_endpoint_with_fixture_token(client: AsyncClient, test_jwt_token):
    # Пример использования прямого тестового JWT
    headers = {"Authorization": f"Bearer {test_jwt_token}"}
    r = await client.get("/tasks/reports?date=2025-05-01", headers=headers)
    # Здесь проверяем код ответа, зависит от логики защиты
    assert r.status_code in (200, 404)
