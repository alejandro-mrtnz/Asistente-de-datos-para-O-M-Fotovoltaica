"""Acceso a la base de datos con controles que NO dependen del LLM.

El modelo propone SQL; este módulo decide qué se ejecuta:
  1. La base de datos se abre en solo lectura (mode=ro).
  2. Un autorizador de SQLite solo permite leer y deniega las columnas con datos personales.
  3. Una sola sentencia por llamada, un máximo de filas devueltas y un tiempo máximo.
"""
from __future__ import annotations  # permite las anotaciones modernas en Python 3.8

import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "pv_om.sqlite"
MAX_ROWS = 100
TIMEOUT_SECONDS = 5
BLOCKED_COLUMNS = {("technicians", "email"), ("technicians", "phone")}

# Diccionario de datos mínimo: el "grano" de cada tabla (qué representa una fila) y sus unidades.
# Sin esto, el agente unió tablas de distinto grano y sumó la irradiación una vez por inversor (evaluación v1, q03).
TABLE_NOTES = {
    "plants": "Una fila por planta. dc_capacity_mwp en MWp (x1000 para kWp); ac_capacity_mw en MW.",
    "inverters": "Una fila por inversor. dc_capacity_kwp = potencia DC conectada a ese inversor (kWp).",
    "daily_irradiation": "Una fila por PLANTA y día. Irradiación en el plano de los módulos (POA), en kWh/m2.",
    "inverter_daily": "Una fila por INVERSOR y día: energía AC (kWh), horas disponibles y horas esperadas.",
    "alarms": "Una fila por alarma de un inversor. ended_at_utc vacío = alarma activa al final de los datos.",
    "technicians": "Una fila por técnico. email y phone están bloqueados (datos personales).",
    "work_orders": "Una fila por orden de trabajo. closed_at_utc vacío = orden abierta. cost_eur = coste de la "
                   "intervención de mantenimiento, en euros.",
}
COVERAGE_SQL = "SELECT MIN(date), MAX(date) FROM inverter_daily"  # periodo que cubren los datos

_ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                    getattr(sqlite3, "SQLITE_RECURSIVE", 33)}


def _authorizer(action, arg1, arg2, _db_name, _trigger):
    """SQLite llama a esta función por cada operación que va a hacer una consulta."""
    if action not in _ALLOWED_ACTIONS:
        return sqlite3.SQLITE_DENY  # INSERT, UPDATE, DELETE, DROP, PRAGMA, ATTACH...
    if action == sqlite3.SQLITE_READ and ((arg1 or "").lower(), (arg2 or "").lower()) in BLOCKED_COLUMNS:
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _open(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}. Ejecuta antes: python data/generate_db.py")
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)  # as_uri() también funciona en Windows


class Database:
    def __init__(self, path: Path = DB_PATH):
        # Conexión del sistema: la usa nuestro código para leer el esquema. El LLM nunca escribe SQL aquí.
        self._meta = _open(path)
        # Conexión del agente: todo el SQL que propone el LLM pasa por aquí, con el autorizador puesto.
        self._agent = _open(path)
        self._agent.set_authorizer(_authorizer)

    def list_tables(self) -> list[dict]:
        names = [r[0] for r in self._meta.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]
        return [{"table": n, "rows": self._meta.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]} for n in names]

    def describe_table(self, table: str) -> dict:
        if table not in {t["table"] for t in self.list_tables()}:  # evita inyectar SQL por el nombre
            return {"error": f"La tabla '{table}' no existe. Usa list_tables."}
        columns = [{"name": c[1], "type": c[2], "not_null": bool(c[3]), "primary_key": bool(c[5])}
                   for c in self._meta.execute(f'PRAGMA table_info("{table}")')]
        visible = [c["name"] for c in columns if (table.lower(), c["name"].lower()) not in BLOCKED_COLUMNS]
        for c in columns:
            if c["name"] not in visible:
                c["note"] = "columna bloqueada: datos personales"
        foreign_keys = [{"column": f[3], "references": f"{f[2]}.{f[4]}"}
                        for f in self._meta.execute(f'PRAGMA foreign_key_list("{table}")')]
        # Filas de ejemplo SIN las columnas bloqueadas: también podrían filtrar datos personales.
        cols_sql = ", ".join(f'"{c}"' for c in visible)
        sample = self._meta.execute(f'SELECT {cols_sql} FROM "{table}" LIMIT 3').fetchall()
        return {"table": table, "grain_and_units": TABLE_NOTES.get(table, ""), "columns": columns,
                "foreign_keys": foreign_keys, "sample_rows": [dict(zip(visible, row)) for row in sample]}

    def data_coverage(self) -> tuple[str, str]:
        start, end = self._meta.execute(COVERAGE_SQL).fetchone()
        return start, end

    def run_sql(self, sql: str) -> dict:
        start = time.monotonic()
        # Si la consulta tarda más de TIMEOUT_SECONDS, SQLite la interrumpe.
        self._agent.set_progress_handler(lambda: int(time.monotonic() - start > TIMEOUT_SECONDS), 10_000)
        try:
            cursor = self._agent.execute(sql)  # sqlite3 rechaza más de una sentencia
            rows = cursor.fetchmany(MAX_ROWS + 1)
        except (sqlite3.Error, sqlite3.Warning) as exc:  # denegado, sintaxis, varias sentencias, tiempo agotado...
            return {"error": f"{type(exc).__name__}: {exc}"}
        finally:
            self._agent.set_progress_handler(None, 0)
        if cursor.description is None:
            return {"error": "La sentencia no devuelve filas. Solo se permiten consultas SELECT."}
        return {"columns": [d[0] for d in cursor.description], "rows": [list(r) for r in rows[:MAX_ROWS]],
                "truncated": len(rows) > MAX_ROWS, "elapsed_ms": round((time.monotonic() - start) * 1000)}
