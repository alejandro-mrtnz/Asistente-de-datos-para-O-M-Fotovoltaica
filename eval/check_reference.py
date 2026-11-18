"""Ejecuta el SQL de referencia de cada caso respondible y comprueba que devuelve los valores esperados.

Uso (desde la carpeta agente-datos):  python eval/check_reference.py
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "pv_om.sqlite"
CASES = ROOT / "eval" / "cases.json"


def found(expected, cells) -> bool:
    if isinstance(expected, str):
        return any(isinstance(v, str) and expected.lower() in v.lower() for v in cells)
    return any(isinstance(v, (int, float)) and abs(v - expected) <= 0.001 * abs(expected) + 1e-9 for v in cells)


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    con = sqlite3.connect(DB.as_uri() + "?mode=ro", uri=True)  # solo lectura
    failures = 0
    for case in cases:
        if case["category"] != "answerable":
            continue
        rows = con.execute(case["reference_sql"]).fetchall()
        cells = [v for row in rows for v in row]
        missing = [e for e in case["expected_values"] if not found(e, cells)]
        failures += bool(missing)
        print(f"{case['id']}  {'OK   ' if not missing else 'FALLA'}  {case['question']}")
        print(f"      resultado: {rows}" + (f"  | falta: {missing}" if missing else ""))
    print(f"\n{'Todo correcto' if not failures else f'{failures} casos fallan'}")


if __name__ == "__main__":
    main()
