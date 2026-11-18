import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from storage import (
    CATEGORIES,
    DIETARY_OPTIONS,
    ImageService,
    MenuRepository,
    parse_bool,
    parse_float,
    parse_int,
)

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "grand-hotel-aurelia-secret-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max upload

repo = MenuRepository()
image_service = ImageService()


def _extract_dietary_from_request(req) -> List[str]:
    if req.is_json:
        data = req.get_json(silent=True) or {}
        raw = data.get("dietary", [])
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
        if isinstance(raw, str):
            return [x.strip() for x in raw.split(",") if x.strip()]
        return []
    dietary_list = req.form.getlist("dietary")
    if dietary_list:
        return [d.strip() for d in dietary_list if d.strip()]
    dietary_csv = req.form.get("dietary_csv", "")
    if dietary_csv:
        return [d.strip() for d in dietary_csv.split(",") if d.strip()]
    return []


def _compute_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(items)
    available_count = sum(1 for i in items if i.get("available", True))
    featured_count = sum(1 for i in items if i.get("featured", False))
    categories_present = sorted({i.get("category", "Platos Fuertes") for i in items})
    avg_price = (
        round(sum(parse_float(i.get("price"), 0.0) for i in items) / total, 2)
        if total > 0
        else 0.0
    )
    return {
        "total": total,
        "available": available_count,
        "unavailable": total - available_count,
        "featured": featured_count,
        "categoriesCount": len(categories_present),
        "avgPrice": avg_price,
    }


@app.route("/")
def index():
    items = repo.list_items()
    stats = _compute_stats(items)
    return render_template(
        "index.html",
        items=items,
        categories=CATEGORIES,
        dietary_options=DIETARY_OPTIONS,
        stats=stats,
        backend_mode=repo.backend_mode,
    )


@app.route("/add", methods=["POST"])
def add_item():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip()
    if not name or not description:
        flash("Por favor completa el nombre y la descripción del platillo.", "error")
        return redirect(url_for("index"))

    price = parse_float(request.form.get("price"), default=250.0)
    category = request.form.get("category") or "Platos Fuertes"
    prep_time = (request.form.get("prepTime") or "15-20 min").strip()
    calories = parse_int(request.form.get("calories"), default=None)
    available = parse_bool(request.form.get("available"), default=True)
    featured = parse_bool(request.form.get("featured"), default=False)
    dietary = _extract_dietary_from_request(request)

    image_file = request.files.get("image")
    image_url_input = (request.form.get("imageUrl") or "").strip()

    try:
        image_url = image_service.save_image(
            image_file,
            fallback_url=image_url_input or "/static/images/ribeye.jpg",
        )
    except ValueError as err:
        flash(str(err), "error")
        return redirect(url_for("index"))

    repo.create_item(
        {
            "name": name,
            "description": description,
            "price": price,
            "category": category,
            "dietary": dietary,
            "prepTime": prep_time,
            "calories": calories,
            "available": available,
            "featured": featured,
            "imageUrl": image_url,
        }
    )
    flash(f'Platillo "{name}" agregado exitosamente a la carta.', "success")
    return redirect(url_for("index"))


@app.route("/delete/<item_id>", methods=["POST"])
def delete_item(item_id: str):
    existing = repo.get_item(item_id)
    deleted = repo.delete_item(item_id)
    if deleted:
        dish_name = existing["name"] if existing else "Platillo"
        flash(f'"{dish_name}" fue eliminado del menú.', "info")
    else:
        flash("No se encontró el platillo que intentabas eliminar.", "error")
    return redirect(url_for("index"))


@app.route("/edit/<item_id>", methods=["GET"])
def edit_item(item_id: str):
    item = repo.get_item(item_id)
    if not item:
        flash("El platillo solicitado no existe.", "error")
        return redirect(url_for("index"))
    return render_template(
        "edit.html",
        item=item,
        categories=CATEGORIES,
        dietary_options=DIETARY_OPTIONS,
    )


@app.route("/update/<item_id>", methods=["POST"])
def update_item(item_id: str):
    existing = repo.get_item(item_id)
    if not existing:
        flash("El platillo solicitado no existe.", "error")
        return redirect(url_for("index"))

    name = (request.form.get("name") or existing["name"]).strip()
    description = (request.form.get("description") or existing["description"]).strip()
    price = (
        parse_float(request.form.get("price"), default=existing.get("price", 250.0))
        if "price" in request.form
        else existing.get("price", 250.0)
    )
    category = request.form.get("category") or existing.get("category", "Platos Fuertes")
    prep_time = (
        (request.form.get("prepTime") or existing.get("prepTime", "15-20 min")).strip()
    )
    calories = (
        parse_int(request.form.get("calories"), default=None)
        if "calories" in request.form
        else existing.get("calories")
    )

    if "available_present" in request.form:
        available = parse_bool(request.form.get("available"), default=False)
    elif "available" in request.form:
        available = parse_bool(request.form.get("available"), default=True)
    else:
        available = existing.get("available", True)

    if "featured_present" in request.form:
        featured = parse_bool(request.form.get("featured"), default=False)
    elif "featured" in request.form:
        featured = parse_bool(request.form.get("featured"), default=False)
    else:
        featured = existing.get("featured", False)

    if "dietary_present" in request.form or "dietary" in request.form:
        dietary = _extract_dietary_from_request(request)
    else:
        dietary = existing.get("dietary", [])

    update_data: Dict[str, Any] = {
        "name": name,
        "description": description,
        "price": price,
        "category": category,
        "prepTime": prep_time,
        "calories": calories,
        "available": available,
        "featured": featured,
        "dietary": dietary,
    }

    image_file = request.files.get("image")
    image_url_input = (request.form.get("imageUrl") or "").strip()

    try:
        new_image_url = image_service.save_image(
            image_file,
            fallback_url=image_url_input if image_url_input else None,
        )
    except ValueError as err:
        flash(str(err), "error")
        return redirect(url_for("edit_item", item_id=item_id))

    if new_image_url:
        # Fixed bug: previously wrote 'imageURL' instead of 'imageUrl'
        update_data["imageUrl"] = new_image_url

    repo.update_item(item_id, update_data)
    flash(f'Platillo "{name}" actualizado correctamente.', "success")
    return redirect(url_for("index"))


@app.route("/toggle/<item_id>", methods=["POST"])
def toggle_item_availability(item_id: str):
    existing = repo.get_item(item_id)
    if not existing:
        if request.headers.get("Accept") == "application/json" or request.is_json:
            return jsonify({"error": "Platillo no encontrado"}), 404
        flash("Platillo no encontrado.", "error")
        return redirect(url_for("index"))

    new_status = not existing.get("available", True)
    updated = repo.update_item(item_id, {"available": new_status})
    if request.headers.get("Accept") == "application/json" or request.is_json:
        return jsonify({"item": updated, "stats": _compute_stats(repo.list_items())})

    status_label = "Disponible" if new_status else "Agotado temporalmente"
    flash(f'Estado de "{existing["name"]}": {status_label}.', "info")
    return redirect(url_for("index"))


# --- REST API ENDPOINTS FOR MODERN UX ---


@app.route("/api/items", methods=["GET"])
def api_list_items():
    items = repo.list_items()
    return jsonify(
        {
            "items": items,
            "stats": _compute_stats(items),
            "categories": CATEGORIES,
            "dietaryOptions": DIETARY_OPTIONS,
        }
    )


@app.route("/api/items/<item_id>", methods=["GET"])
def api_get_item(item_id: str):
    item = repo.get_item(item_id)
    if not item:
        return jsonify({"error": "Platillo no encontrado"}), 404
    return jsonify({"item": item})


@app.route("/api/items/<item_id>", methods=["DELETE"])
def api_delete_item(item_id: str):
    deleted = repo.delete_item(item_id)
    if not deleted:
        return jsonify({"error": "Platillo no encontrado"}), 404
    items = repo.list_items()
    return jsonify({"deleted": True, "itemId": item_id, "stats": _compute_stats(items)})


@app.route("/api/seed", methods=["POST"])
def api_reset_seed():
    items = repo.reset_seed()
    return jsonify(
        {
            "items": items,
            "stats": _compute_stats(items),
            "message": "Carta restaurada con los platillos de autor del hotel.",
        }
    )


@app.route("/api/order", methods=["POST"])
def api_place_order():
    data = request.get_json(silent=True) or {}
    room_number = str(data.get("roomNumber") or "").strip()
    guest_name = str(data.get("guestName") or "Huésped").strip()
    order_items = data.get("items") or []

    if not room_number:
        return jsonify({"error": "Por favor ingresa tu número de habitación."}), 400
    if not order_items or not isinstance(order_items, list):
        return jsonify({"error": "Tu orden de Room Service está vacía."}), 400

    subtotal = 0.0
    validated_lines = []
    for line in order_items:
        dish = repo.get_item(str(line.get("id", "")))
        qty = max(1, int(line.get("qty", 1)))
        if dish and dish.get("available", True):
            line_total = round(dish["price"] * qty, 2)
            subtotal += line_total
            validated_lines.append(
                {
                    "name": dish["name"],
                    "qty": qty,
                    "unitPrice": dish["price"],
                    "lineTotal": line_total,
                }
            )

    if not validated_lines:
        return jsonify({"error": "Los platillos seleccionados no están disponibles."}), 400

    service_fee = round(subtotal * 0.10, 2)
    total = round(subtotal + service_fee, 2)
    folio = f"RS-{os.urandom(2).hex().upper()}"

    return jsonify(
        {
            "ok": True,
            "folio": folio,
            "roomNumber": room_number,
            "guestName": guest_name,
            "lines": validated_lines,
            "subtotal": subtotal,
            "serviceFee": service_fee,
            "total": total,
            "estimatedDelivery": "25 - 35 min",
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
