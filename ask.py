"""Línea de comandos para hacer preguntas al agente.

Uso:  python ask.py "¿Qué planta tuvo peor disponibilidad en 2025?"
      python ask.py            (modo interactivo; línea vacía para salir)
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from agent import ask, make_client
from db import Database

LOG = Path(__file__).resolve().parent / "logs" / "audit.jsonl"


def show(result: dict) -> None:
    for t in result["trace"]:
        if t["tool"] == "run_sql":
            r = t["result"]
            status = r.get("error") or f"{len(r['rows'])} filas" + (" (truncado)" if r.get("truncated") else "")
            print(f"  [SQL paso {t['step']}] {json.loads(t['args']).get('sql', '')}\n      -> {status}")
        else:
            print(f"  [paso {t['step']}] {t['tool']}({t['args']})")
    print(f"\n{result['answer']}\n")


def log(question: str, model: str, result: dict) -> None:
    """Registro de auditoría: cada pregunta, el SQL ejecutado y la respuesta."""
    LOG.parent.mkdir(exist_ok=True)
    entry = {"ts": datetime.now().isoformat(timespec="seconds"), "model": model, "question": question,
             "sql": [t["args"] for t in result["trace"] if t["tool"] == "run_sql"],
             "answer": result["answer"], "steps": result["steps"], "stopped": result["stopped"]}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    client, model = make_client()
    db = Database()
    questions = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else iter(lambda: input("Pregunta: ").strip(), "")
    for q in questions:
        result = ask(q, client, model, db)
        show(result)
        log(q, model, result)


if __name__ == "__main__":
    main()
