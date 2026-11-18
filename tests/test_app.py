import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import app as flask_app
import storage


@pytest.fixture(autouse=True)
def isolated_repo(tmp_path, monkeypatch):
    """Isolate the local JSON database and upload folder for each test."""
    test_db_file = tmp_path / "menu_items.json"
    test_upload_dir = tmp_path / "uploads"
    test_upload_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(storage, "LOCAL_DB_FILE", test_db_file)
    monkeypatch.setattr(storage, "UPLOAD_FOLDER", test_upload_dir)

    repo = storage.MenuRepository(mongo_collection=None)
    monkeypatch.setattr(flask_app, "repo", repo)

    img_service = storage.ImageService()
    img_service.use_cloudinary = False
    monkeypatch.setattr(flask_app, "image_service", img_service)

    flask_app.app.config["TESTING"] = True
    return repo


@pytest.fixture
def client():
    with flask_app.app.test_client() as c:
        yield c


def test_index_renders_seeded_dishes(client):
    res = client.get("/")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Menú del Hotel" in html
    assert "Ribeye Prime Añejado al Romero" in html
    assert "Burrata Pugliese" in html


def test_add_item_with_image_upload(client, isolated_repo):
    fake_image = (io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimagebytes"), "platillo_nuevo.png")
    res = client.post(
        "/add",
        data={
            "name": "Tartar de Atún Aleta Azul",
            "description": "Atún fresco cortado a cuchillo con aguacate, ajonjolí negro y ponzu cítrico.",
            "price": "410.50",
            "category": "Entradas",
            "prepTime": "12 min",
            "dietary": ["Sin Gluten", "Especial del Chef"],
            "featured": "true",
            "image": fake_image,
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Tartar de Atún Aleta Azul" in html
    assert "410.50" in html

    items = isolated_repo.list_items()
    created = next(i for i in items if i["name"] == "Tartar de Atún Aleta Azul")
    assert created["price"] == 410.50
    assert created["category"] == "Entradas"
    assert "Sin Gluten" in created["dietary"]
    assert created["imageUrl"].startswith("/static/uploads/dish_")


def test_update_item_fixes_imageUrl_bug(client, isolated_repo):
    items = isolated_repo.list_items()
    target = items[0]
    item_id = target["_id"]

    # Edit page loads
    edit_res = client.get(f"/edit/{item_id}")
    assert edit_res.status_code == 200
    assert target["name"] in edit_res.get_data(as_text=True)

    # Update item including a new uploaded image
    new_photo = (io.BytesIO(b"\xff\xd8\xff\xe0fakejpeg"), "updated_dish.jpg")
    upd_res = client.post(
        f"/update/{item_id}",
        data={
            "name": "Huevos Benedictinos Imperiales",
            "description": "Versión renovada con caviar y trufa blanca.",
            "price": "365.00",
            "category": "Desayunos",
            "available_present": "1",
            "available": "true",
            "image": new_photo,
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert upd_res.status_code == 200

    updated = isolated_repo.get_item(item_id)
    assert updated is not None
    assert updated["name"] == "Huevos Benedictinos Imperiales"
    assert updated["price"] == 365.00
    assert updated["imageUrl"].startswith("/static/uploads/dish_")
    assert updated["imageUrl"].endswith(".jpg")


def test_toggle_and_delete_item(client, isolated_repo):
    items = isolated_repo.list_items()
    item_id = items[0]["_id"]
    assert items[0]["available"] is True

    # Toggle availability off
    res = client.post(f"/toggle/{item_id}", follow_redirects=True)
    assert res.status_code == 200
    after_toggle = isolated_repo.get_item(item_id)
    assert after_toggle["available"] is False

    # Delete item
    del_res = client.post(f"/delete/{item_id}", follow_redirects=True)
    assert del_res.status_code == 200
    assert isolated_repo.get_item(item_id) is None


def test_room_service_order_endpoint(client, isolated_repo):
    items = isolated_repo.list_items()
    first = items[0]

    res = client.post(
        "/api/order",
        json={
            "roomNumber": "Suite 501",
            "guestName": "Sr. Rivera",
            "items": [{"id": first["_id"], "qty": 2}],
        },
    )
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["ok"] is True
    assert payload["roomNumber"] == "Suite 501"
    expected_subtotal = round(first["price"] * 2, 2)
    expected_fee = round(expected_subtotal * 0.10, 2)
    assert payload["subtotal"] == expected_subtotal
    assert payload["serviceFee"] == expected_fee
    assert payload["total"] == round(expected_subtotal + expected_fee, 2)
    assert payload["folio"].startswith("RS-")


def test_legacy_item_normalization():
    legacy_doc = {
        "_id": "507f1f77bcf86cd799439011",
        "name": "Chilaquiles del Chef",
        "description": "Salsa verde tatemada con crema de rancho.",
        "imageURL": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
    }
    norm = storage.normalize_item(legacy_doc)
    assert norm["imageUrl"] == "https://res.cloudinary.com/demo/image/upload/sample.jpg"
    assert norm["price"] == 250.0
    assert norm["category"] == "Platos Fuertes"
    assert norm["available"] is True
