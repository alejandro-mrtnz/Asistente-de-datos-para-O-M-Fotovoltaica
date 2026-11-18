"""Compara dos evaluaciones caso a caso (por defecto, las dos más recientes).

Uso (desde la carpeta agente-datos):
    python eval/compare_runs.py
    python eval/compare_runs.py eval/results/run_A.json eval/results/run_B.json
"""
import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"


def load(path: Path) -> dict:
    run = json.loads(path.read_text(encoding="utf-8"))
    run["file"] = path.name
    return run


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:3]] or sorted(RESULTS.glob("run_*.json"))[-2:]
    if len(paths) < 2:
        sys.exit("Hacen falta dos evaluaciones en eval/results/.")
    a, b = load(paths[0]), load(paths[1])
    label = lambda r: f"{r.get('agent_version', 'v1')} ({r['file']})"  # noqa: E731
    print(f"A = {label(a)}\nB = {label(b)}\n")
    by_id = {c["id"]: c for c in a["cases"]}
    print(f"{'caso':6}{'A':16}{'B':16}{'pasos A→B':12}pregunta")
    for cb in b["cases"]:
        ca = by_id.get(cb["id"])
        va = ca["grading"]["verdict"] if ca else "—"
        steps = f"{ca['steps'] if ca else '—'}→{cb['steps']}"
        print(f"{cb['id']:6}{va:16}{cb['grading']['verdict']:16}{steps:12}{cb['question'][:60]}")
    print("\nRespuestas de los casos de revisión manual (B):")
    for cb in b["cases"]:
        if cb["grading"]["verdict"] in ("revisar", "fallo"):
            print(f"\n[{cb['id']}] {' '.join(cb['answer'].split())[:400]}")


if __name__ == "__main__":
    main()
