# Grand Hotel Aurelia · Carta Gastronómica & Room Service

Aplicación web full-stack en **Flask (Python)** para la gestión digital del menú de un hotel y pedidos de **Room Service**. Combina una experiencia editorial para los huéspedes con un panel de administración ágil para el chef o personal del restaurante.

---

## Características Principales

### Experiencia del Huésped (Carta Digital & Room Service)
- **Filtro interactivo por categorías**: *Desayunos, Entradas, Platos Fuertes, Postres y Bebidas*.
- **Filtros por preferencias dietéticas**: *Especial del Chef, Sin Gluten, Vegetariano, Vegano y Orgánico*.
- **Búsqueda en tiempo real y ordenamiento**: Filtra instantáneamente por nombre o ingrediente y ordena por platillos destacados, precio o alfabéticamente.
- **Bandeja de Room Service**: Carrito interactivo con ajuste de cantidades, cálculo automático de cargo por servicio a habitación (10%) y confirmación de pedido con generación de número de folio (`RS-XXXX`).

### Modo Chef / Administración
- **Conmutador de vista instantáneo**: Alterna entre **Vista Huésped** y **Modo Chef / Admin** desde la barra superior.
- **Gestión completa de platillos (CRUD)**: Agrega nuevos platillos, edita información, precios, tiempos de preparación, etiquetas dietéticas y fotografías.
- **Vista previa de imagen en vivo**: Previsualiza archivos locales (`JPG`, `PNG`, `WEBP`, `GIF`, `AVIF`) o enlaces URL antes de guardar.
- **Control rápido de disponibilidad**: Marca cualquier platillo como *Disponible* o *Agotado temporalmente* con un solo clic.
- **Confirmación de seguridad**: Modal de confirmación antes de eliminar un platillo de la carta.

### Arquitectura de Persistencia Híbrida (Funciona sin configuración externa)
- **Base de datos**: Se conecta automáticamente a **MongoDB** si se define `MONGO_URI` en el archivo `.env`. Si no se configura o no hay conexión, utiliza automáticamente almacenamiento local persistente en `data/menu_items.json` precargado con 6 platillos de autor.
- **Almacenamiento de imágenes**: Sube imágenes a **Cloudinary** cuando se configuran sus credenciales en `.env`, o las guarda automáticamente de forma local en `static/uploads/` cuando se ejecuta sin cuenta de Cloudinary.

---

## Estructura del Proyecto

```text
menu-hotel-/
├── app.py                  # Aplicación principal Flask, rutas vistas y endpoints API REST
├── storage.py              # Capa de datos híbrida (MongoDB / JSON local) y subida de imágenes
├── requirements.txt        # Dependencias de Python
├── Procfile                # Configuración para despliegue con Gunicorn
├── .env.example            # Plantilla de variables de entorno opcionales
├── data/
│   └── menu_items.json     # Base de datos local por defecto con platillos iniciales
├── static/
│   ├── style.css           # Sistema de diseño editorial y estilos responsivos
│   ├── app.js              # Lógica interactiva de filtros, modales y carrito Room Service
│   ├── images/             # Fotografías gastronómicas iniciales de la carta
│   └── uploads/            # Imágenes subidas localmente cuando no se usa Cloudinary
├── templates/
│   ├── index.html          # Vista principal de la carta, filtros, carrito y modal de alta
│   └── edit.html           # Vista dedicada para edición detallada de platillos
└── tests/
    └── test_app.py         # Pruebas automatizadas con pytest
```

---

## Cómo Ejecutar el Proyecto en Local

### 1. Prerrequisitos
- **Python 3.10+** instalado en tu sistema.
- **Git** para clonar el repositorio.

### 2. Clonar el repositorio
```bash
git clone https://github.com/xltsignosis/menu-hotel-.git
cd menu-hotel-
```

### 3. Crear y activar un entorno virtual

**En Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**En Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4. Instalar las dependencias
```bash
pip install -r requirements.txt
```

### 5. Configurar variables de entorno *(Opcional)*
> **Nota:** La aplicación funciona **de inmediato sin necesidad de crear un archivo `.env`** usando almacenamiento local en `data/menu_items.json` y `static/uploads/`.

Si deseas conectarla a tu propio clúster de **MongoDB Atlas** y cuenta de **Cloudinary**, copia el archivo de ejemplo y agrega tus credenciales:
```bash
cp .env.example .env
```
Contenido de `.env`:
```env
MONGO_URI=mongodb+srv://usuario:password@cluster.mongodb.net/menuDB
CLOUD_NAME=tu_cloud_name
CLOUD_API_KEY=tu_api_key
CLOUD_API_SECRET=tu_api_secret
SECRET_KEY=clave-secreta-segura-del-hotel
PORT=5000
```

### 6. Iniciar el servidor de desarrollo
```bash
python app.py
```
O bien utilizando **Gunicorn** (entorno tipo producción en Linux/macOS):
```bash
gunicorn --bind 0.0.0.0:5000 app:app
```

Abre tu navegador en:
**`http://localhost:5000`**

---

## Ejecutar las Pruebas Automatizadas

El proyecto incluye pruebas unitarias y de integración con `pytest` para verificar el listado de la carta, alta con subida de imágenes, actualización de platillos, cambio de disponibilidad y cálculo de órdenes de Room Service:

```bash
pip install pytest
pytest -v
```

---

## Rutas y Endpoints Principales

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `/` | Renderiza la carta principal del hotel con estadísticas y filtros. |
| `POST` | `/add` | Agrega un nuevo platillo a la carta (soporta archivo de imagen o URL). |
| `GET` | `/edit/<item_id>` | Muestra el formulario de edición detallada de un platillo. |
| `POST` | `/update/<item_id>` | Actualiza los datos e imagen de un platillo existente. |
| `POST` | `/toggle/<item_id>` | Alterna el estado de un platillo entre *Disponible* y *Agotado*. |
| `POST` | `/delete/<item_id>` | Elimina un platillo de la carta. |
| `GET` | `/api/items` | Devuelve en formato JSON todos los platillos y estadísticas. |
| `POST` | `/api/order` | Procesa una orden de Room Service y devuelve el folio y desglose. |
| `POST` | `/api/seed` | Restaura la carta con los 6 platillos de autor iniciales. |

---

## 📄 Licencia
Distribuido bajo la licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.
