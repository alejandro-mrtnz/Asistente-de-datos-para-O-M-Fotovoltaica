"""Muestra la respuesta completa y el SQL de algunos casos de la última evaluación.

Uso (desde la carpeta agente-datos):  python eval/show_cases.py q03 u01 u02
"""
import json
import sys
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"

latest = sorted(RESULTS.glob("run_*.json"))[-1]
run = json.loads(latest.read_text(encoding="utf-8"))
wanted = set(sys.argv[1:])
print(f"Fichero: {latest.name} · modelo {run['model']}")
for case in run["cases"]:
    if wanted and case["id"] not in wanted:
        continue
    print(f"\n=== {case['id']} · {case['grading']['verdict']} · {case['steps']} pasos · {case['question']}")
    for t in case["trace"]:
        if t["tool"] == "run_sql":
            r = t["result"]
            out = r.get("error") or f"{r['rows'][:5]}{' ...' if len(r['rows']) > 5 else ''}"
            print(f"  [SQL paso {t['step']}] {' '.join(json.loads(t['args']).get('sql', '').split())}\n      -> {out}")
        else:
            print(f"  [paso {t['step']}] {t['tool']}({t['args']})")
    print(f"\n  RESPUESTA: {case['answer']}")
