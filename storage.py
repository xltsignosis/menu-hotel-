import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import cloudinary
import cloudinary.uploader
from bson.objectid import ObjectId
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOCAL_DB_FILE = DATA_DIR / "menu_items.json"
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "avif"}

CATEGORIES = [
    "Desayunos",
    "Entradas",
    "Platos Fuertes",
    "Postres",
    "Bebidas",
]

DIETARY_OPTIONS = [
    "Especial del Chef",
    "Sin Gluten",
    "Vegetariano",
    "Vegano",
    "Picante",
    "Orgánico",
]

DEFAULT_SEED_ITEMS: List[Dict[str, Any]] = [
    {
        "_id": "66b0a1000000000000000001",
        "name": "Huevos Benedictinos Royale",
        "description": "Pan brioche artesanal tostado a la mantequilla con salmón ahumado del Atlántico, huevos pochados de granja, salsa holandesa sedosa al limón y jitomates cherry confitados.",
        "price": 295.0,
        "category": "Desayunos",
        "dietary": ["Especial del Chef", "Orgánico"],
        "prepTime": "15 min",
        "calories": 580,
        "available": True,
        "featured": True,
        "imageUrl": "/static/images/benedict.jpg",
    },
    {
        "_id": "66b0a1000000000000000002",
        "name": "Burrata Pugliese & Jitomates Heirloom",
        "description": "Burrata cremosa importada servida sobre jitomates reliquia de huerta local, hojas de albahaca fresca, aceite de oliva extra virgen prensado en frío y reducción de balsámico añejo.",
        "price": 340.0,
        "category": "Entradas",
        "dietary": ["Vegetariano", "Sin Gluten", "Orgánico"],
        "prepTime": "10 min",
        "calories": 420,
        "available": True,
        "featured": False,
        "imageUrl": "/static/images/burrata.jpg",
    },
    {
        "_id": "66b0a1000000000000000003",
        "name": "Ribeye Prime Añejado al Romero",
        "description": "Corte Ribeye Prime de 400g sellado a las brasas con mantequilla de ajo rostizado y romero fresco, acompañado de puré rústico de papa con trufa negra.",
        "price": 780.0,
        "category": "Platos Fuertes",
        "dietary": ["Especial del Chef", "Sin Gluten"],
        "prepTime": "25 min",
        "calories": 890,
        "available": True,
        "featured": True,
        "imageUrl": "/static/images/ribeye.jpg",
    },
    {
        "_id": "66b0a1000000000000000004",
        "name": "Salmón del Atlántico al Azafrán y Cítricos",
        "description": "Filete de salmón con piel crujiente glaseado en reducción de naranja sanguina y hebras de azafrán español, sobre espárragos verdes a la parrilla y brotes orgánicos.",
        "price": 560.0,
        "category": "Platos Fuertes",
        "dietary": ["Sin Gluten", "Orgánico"],
        "prepTime": "20 min",
        "calories": 610,
        "available": True,
        "featured": True,
        "imageUrl": "/static/images/salmon.jpg",
    },
    {
        "_id": "66b0a1000000000000000005",
        "name": "Fondant Tibio de Chocolate Valrhona 70%",
        "description": "Volcán de chocolate oscuro con centro líquido, acompañado de helado artesanal de vainilla de Papantla, frambuesas frescas, crumble de almendra y lámina de oro comestible.",
        "price": 265.0,
        "category": "Postres",
        "dietary": ["Vegetariano", "Especial del Chef"],
        "prepTime": "18 min",
        "calories": 540,
        "available": True,
        "featured": True,
        "imageUrl": "/static/images/fondant.jpg",
    },
    {
        "_id": "66b0a1000000000000000006",
        "name": "Elixir Botánico Ahumado",
        "description": "Cóctel de autor con bourbon reposado, licor de naranja sanguina, amargo de angostura y esfera de hielo cristalino perfumado con humo de romero silvestre.",
        "price": 240.0,
        "category": "Bebidas",
        "dietary": ["Vegano", "Sin Gluten"],
        "prepTime": "5 min",
        "calories": 195,
        "available": True,
        "featured": False,
        "imageUrl": "/static/images/cocktail.jpg",
    },
]


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return round(max(0.0, float(cleaned)), 2)
    except (ValueError, TypeError):
        return default


def parse_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    try:
        return max(0, int(float(str(value).strip())))
    except (ValueError, TypeError):
        return default


def parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    val = str(value).strip().lower()
    if val in ("true", "1", "on", "yes", "si", "sí"):
        return True
    if val in ("false", "0", "off", "no"):
        return False
    return default


def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure every item dictionary has consistent keys and types, fixing legacy imageURL typos."""
    item_id = str(raw.get("_id", ""))
    image_url = (
        raw.get("imageUrl")
        or raw.get("imageURL")
        or "/static/images/ribeye.jpg"
    )
    category = raw.get("category") or "Platos Fuertes"
    if category not in CATEGORIES:
        category = "Platos Fuertes"

    dietary = raw.get("dietary")
    if isinstance(dietary, str):
        dietary = [d.strip() for d in dietary.split(",") if d.strip()]
    elif not isinstance(dietary, list):
        dietary = []

    price = parse_float(raw.get("price"), default=250.0)
    prep_time = str(raw.get("prepTime") or "15-20 min").strip()
    calories = parse_int(raw.get("calories"), default=None)
    available = parse_bool(raw.get("available"), default=True)
    featured = parse_bool(raw.get("featured"), default=False)

    return {
        "_id": item_id,
        "name": str(raw.get("name") or "Platillo sin nombre").strip(),
        "description": str(raw.get("description") or "").strip(),
        "price": price,
        "category": category,
        "dietary": dietary,
        "prepTime": prep_time,
        "calories": calories,
        "available": available,
        "featured": featured,
        "imageUrl": image_url,
        "updatedAt": raw.get("updatedAt") or datetime.now(timezone.utc).isoformat(),
    }


class ImageService:
    """Handles image uploads via Cloudinary when configured, with automatic local filesystem fallback."""

    def __init__(self) -> None:
        UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        self.cloud_name = os.getenv("CLOUD_NAME")
        self.api_key = os.getenv("CLOUD_API_KEY")
        self.api_secret = os.getenv("CLOUD_API_SECRET")
        self.use_cloudinary = bool(self.cloud_name and self.api_key and self.api_secret)

        if self.use_cloudinary:
            cloudinary.config(
                cloud_name=self.cloud_name,
                api_key=self.api_key,
                api_secret=self.api_secret,
            )

    def save_image(
        self,
        file_storage: Optional[FileStorage],
        fallback_url: Optional[str] = None,
    ) -> str:
        if file_storage and file_storage.filename and file_storage.filename.strip():
            filename = secure_filename(file_storage.filename)
            if not allowed_file(filename):
                raise ValueError(
                    "Formato de imagen no permitido. Usa JPG, PNG, WEBP, GIF o AVIF."
                )

            if self.use_cloudinary:
                try:
                    upload_result = cloudinary.uploader.upload(file_storage)
                    if upload_result and upload_result.get("secure_url"):
                        return upload_result["secure_url"]
                except Exception:
                    # Fall back to local storage if Cloudinary upload fails
                    file_storage.stream.seek(0)

            ext = filename.rsplit(".", 1)[1].lower()
            unique_name = f"dish_{uuid.uuid4().hex[:12]}.{ext}"
            target_path = UPLOAD_FOLDER / unique_name
            file_storage.save(str(target_path))
            return f"/static/uploads/{unique_name}"

        if fallback_url and fallback_url.strip():
            return fallback_url.strip()

        return ""


class MenuRepository:
    """Provides CRUD operations backed by MongoDB when available or a persistent JSON file otherwise."""

    def __init__(self, mongo_collection: Optional[Any] = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.mongo_collection = mongo_collection
        self.backend_mode = "local"

        if self.mongo_collection is not None:
            self.backend_mode = "mongodb"
        else:
            mongo_uri = os.getenv("MONGO_URI")
            if mongo_uri:
                try:
                    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
                    client.admin.command("ping")
                    self.mongo_collection = client.menuDB.items
                    self.backend_mode = "mongodb"
                except Exception:
                    self.mongo_collection = None
                    self.backend_mode = "local"

        if self.backend_mode == "local":
            self._ensure_local_seed()

    def _ensure_local_seed(self) -> None:
        if not LOCAL_DB_FILE.exists():
            self._write_local_items(DEFAULT_SEED_ITEMS)
            return
        try:
            with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or len(data) == 0:
                self._write_local_items(DEFAULT_SEED_ITEMS)
        except Exception:
            self._write_local_items(DEFAULT_SEED_ITEMS)

    def _read_local_items(self) -> List[Dict[str, Any]]:
        self._ensure_local_seed()
        with open(LOCAL_DB_FILE, "r", encoding="utf-8") as f:
            items = json.load(f)
        return [normalize_item(item) for item in items]

    def _write_local_items(self, items: List[Dict[str, Any]]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        normalized = [normalize_item(item) for item in items]
        with open(LOCAL_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)

    def list_items(self) -> List[Dict[str, Any]]:
        if self.mongo_collection is not None:
            try:
                docs = list(self.mongo_collection.find())
                return [normalize_item(doc) for doc in docs]
            except PyMongoError:
                pass
        return self._read_local_items()

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        if self.mongo_collection is not None:
            try:
                query = (
                    {"_id": ObjectId(item_id)}
                    if ObjectId.is_valid(item_id)
                    else {"_id": item_id}
                )
                doc = self.mongo_collection.find_one(query)
                return normalize_item(doc) if doc else None
            except PyMongoError:
                pass

        for item in self._read_local_items():
            if str(item["_id"]) == str(item_id):
                return item
        return None

    def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "name": str(data.get("name") or "").strip(),
            "description": str(data.get("description") or "").strip(),
            "price": parse_float(data.get("price"), default=250.0),
            "category": data.get("category") if data.get("category") in CATEGORIES else "Platos Fuertes",
            "dietary": data.get("dietary") if isinstance(data.get("dietary"), list) else [],
            "prepTime": str(data.get("prepTime") or "15-20 min").strip(),
            "calories": parse_int(data.get("calories"), default=None),
            "available": parse_bool(data.get("available"), default=True),
            "featured": parse_bool(data.get("featured"), default=False),
            "imageUrl": data.get("imageUrl") or "/static/images/ribeye.jpg",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        if self.mongo_collection is not None:
            try:
                result = self.mongo_collection.insert_one(payload.copy())
                payload["_id"] = str(result.inserted_id)
                return normalize_item(payload)
            except PyMongoError:
                pass

        items = self._read_local_items()
        payload["_id"] = str(ObjectId())
        items.insert(0, normalize_item(payload))
        self._write_local_items(items)
        return normalize_item(payload)

    def update_item(self, item_id: str, update_fields: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cleaned_update: Dict[str, Any] = {}
        if "name" in update_fields and update_fields["name"] is not None:
            cleaned_update["name"] = str(update_fields["name"]).strip()
        if "description" in update_fields and update_fields["description"] is not None:
            cleaned_update["description"] = str(update_fields["description"]).strip()
        if "price" in update_fields and update_fields["price"] is not None:
            cleaned_update["price"] = parse_float(update_fields["price"], default=250.0)
        if "category" in update_fields and update_fields["category"]:
            cat = str(update_fields["category"]).strip()
            cleaned_update["category"] = cat if cat in CATEGORIES else "Platos Fuertes"
        if "dietary" in update_fields and update_fields["dietary"] is not None:
            dietary = update_fields["dietary"]
            if isinstance(dietary, str):
                dietary = [d.strip() for d in dietary.split(",") if d.strip()]
            cleaned_update["dietary"] = dietary
        if "prepTime" in update_fields and update_fields["prepTime"] is not None:
            cleaned_update["prepTime"] = str(update_fields["prepTime"]).strip() or "15-20 min"
        if "calories" in update_fields:
            cleaned_update["calories"] = parse_int(update_fields["calories"], default=None)
        if "available" in update_fields and update_fields["available"] is not None:
            cleaned_update["available"] = parse_bool(update_fields["available"], default=True)
        if "featured" in update_fields and update_fields["featured"] is not None:
            cleaned_update["featured"] = parse_bool(update_fields["featured"], default=False)
        if update_fields.get("imageUrl"):
            cleaned_update["imageUrl"] = str(update_fields["imageUrl"]).strip()

        cleaned_update["updatedAt"] = datetime.now(timezone.utc).isoformat()

        if self.mongo_collection is not None:
            try:
                query = (
                    {"_id": ObjectId(item_id)}
                    if ObjectId.is_valid(item_id)
                    else {"_id": item_id}
                )
                self.mongo_collection.update_one(query, {"$set": cleaned_update})
                return self.get_item(item_id)
            except PyMongoError:
                pass

        items = self._read_local_items()
        updated_item = None
        for idx, item in enumerate(items):
            if str(item["_id"]) == str(item_id):
                merged = {**item, **cleaned_update}
                updated_item = normalize_item(merged)
                items[idx] = updated_item
                break

        if updated_item:
            self._write_local_items(items)
        return updated_item

    def delete_item(self, item_id: str) -> bool:
        if self.mongo_collection is not None:
            try:
                query = (
                    {"_id": ObjectId(item_id)}
                    if ObjectId.is_valid(item_id)
                    else {"_id": item_id}
                )
                res = self.mongo_collection.delete_one(query)
                return getattr(res, "deleted_count", 1) > 0
            except PyMongoError:
                pass

        items = self._read_local_items()
        filtered = [item for item in items if str(item["_id"]) != str(item_id)]
        if len(filtered) == len(items):
            return False
        self._write_local_items(filtered)
        return True

    def reset_seed(self) -> List[Dict[str, Any]]:
        if self.mongo_collection is not None:
            try:
                self.mongo_collection.delete_many({})
                for seed in DEFAULT_SEED_ITEMS:
                    copy_seed = seed.copy()
                    copy_seed["_id"] = ObjectId(seed["_id"])
                    self.mongo_collection.insert_one(copy_seed)
                return self.list_items()
            except PyMongoError:
                pass

        self._write_local_items(DEFAULT_SEED_ITEMS)
        return self._read_local_items()
