"""Importa el historial de evaluaciones.db a PostgreSQL/Neon sin duplicar IDs.

Uso desde la raíz del repositorio:
    python backend/scripts/migrar_sqlite_a_neon.py
    python backend/scripts/migrar_sqlite_a_neon.py --source /ruta/a/evaluaciones.db

DATABASE_URL debe estar definida en el entorno y apuntar a Neon. El script no
imprime credenciales ni el contenido de las URL/reportes.
"""

import argparse
import asyncio
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=False)

from app.db.database import (  # noqa: E402
    backend_activo,
    close_db,
    importar_tarea,
    init_db,
)


def leer_sqlite(ruta: Path) -> list[dict]:
    if not ruta.is_file():
        raise FileNotFoundError(f"No se encontró el archivo SQLite: {ruta}")

    db = sqlite3.connect(str(ruta))
    db.row_factory = sqlite3.Row
    try:
        columnas = {fila[1] for fila in db.execute("PRAGMA table_info(tareas)")}
        if not columnas:
            raise RuntimeError("El archivo SQLite no contiene la tabla tareas.")
        columna_url = "url" if "url" in columnas else "NULL AS url"
        filas = db.execute(
            f"""
            SELECT id, estado, tiempo_ejecucion_seg, resultado, mensaje,
                   fecha_creacion, {columna_url}
            FROM tareas
            ORDER BY fecha_creacion ASC, id ASC
            """
        ).fetchall()
        return [dict(fila) for fila in filas]
    finally:
        db.close()


async def ejecutar(ruta_origen: Path):
    if backend_activo() != "postgresql":
        raise RuntimeError(
            "Configura DATABASE_URL con la cadena de conexión PostgreSQL de Neon antes de migrar."
        )

    registros = leer_sqlite(ruta_origen)
    await init_db()
    importados = 0
    existentes = 0
    try:
        for registro in registros:
            if await importar_tarea(registro):
                importados += 1
            else:
                existentes += 1
    finally:
        await close_db()

    print(f"Registros leídos desde SQLite: {len(registros)}")
    print(f"Registros importados a Neon: {importados}")
    print(f"Registros omitidos por ID ya existente: {existentes}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_DIR / "evaluaciones.db",
        help="Ruta del archivo SQLite de origen (por defecto backend/evaluaciones.db).",
    )
    args = parser.parse_args()
    asyncio.run(ejecutar(args.source.resolve()))


if __name__ == "__main__":
    main()
