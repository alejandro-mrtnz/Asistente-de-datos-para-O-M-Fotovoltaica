# Asistente de datos para O&M fotovoltaico

Plataforma agéntica sobre una base de datos: un LLM con tres herramientas responde, en español, preguntas
de un responsable de operación y mantenimiento (O&M) sobre una cartera de plantas fotovoltaicas.
El modelo propone SQL; el código y la base de datos deciden qué se ejecuta.

> **Los datos son sintéticos.** Plantas, fabricantes, técnicos y cifras son inventados y se generan con una
> semilla fija (`data/generate_db.py`). No proceden de ninguna empresa.

El informe con el diseño, las decisiones y los resultados se entrega aparte, en PDF.

## Requisitos

- Python 3.10 o superior (probado con Python 3.13 en Windows).
- Una API key de un proveedor compatible con la API de OpenAI. Por defecto, Gemini (nivel gratuito de Google AI Studio).

## Instalación

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows (PowerShell)   ·   source .venv/bin/activate  en macOS/Linux
python -m pip install -r requirements.txt
python data/generate_db.py         # crea data/pv_om.sqlite (45 inversores, 820 alarmas, 143 órdenes)
```

**Configuración de la clave (no se incluye ninguna en el repositorio):**

```bash
copy .env.example .env             # Windows   ·   cp .env.example .env  en macOS/Linux
```

Edita `.env` y rellena `LLM_API_KEY`. El fichero `.env` está en `.gitignore`.
`LLM_BASE_URL` y `LLM_MODEL` permiten cambiar de proveedor o de modelo sin tocar el código
(en `.env.example` hay ejemplos para Groq y Ollama).

Comprueba la conexión con el proveedor (no muestra la clave):

```bash
python check_llm.py
```

## Uso

```bash
python ask.py "¿Qué planta tuvo peor disponibilidad en 2025?"
python ask.py                      # modo interactivo; línea vacía para salir
```

Cada respuesta muestra las herramientas usadas y el SQL ejecutado. Todas las preguntas quedan registradas en
`logs/audit.jsonl` (pregunta, SQL, respuesta, pasos).

## Evaluación

```bash
python eval/check_reference.py     # el SQL de referencia devuelve los valores esperados (sin LLM)
python eval/test_controls.py       # 13 consultas peligrosas contra la capa de control + 3 comprobaciones (sin LLM)
python eval/run_eval.py --pause 10 # ejecuta los 20 casos contra el agente y guarda resultados en eval/results/
python eval/compare_runs.py        # compara las dos últimas ejecuciones caso a caso
python eval/show_cases.py q03 u01  # respuesta completa y SQL de algunos casos de la última ejecución
```

`eval/results/` contiene las ejecuciones reales citadas en el informe.

## Estructura

```
agent.py              agente: prompt, herramientas y bucle (máx. 10 pasos)
db.py                 capa de control: solo lectura, autorizador SQLite, límites, diccionario de datos
ask.py                línea de comandos y registro de auditoría
check_llm.py          diagnóstico de la conexión con el proveedor
data/generate_db.py   generador de la base de datos sintética (semilla 42)
eval/cases.json       20 casos: 10 + 1 con respuesta conocida, 3 + 2 sin respuesta, 4 ataques
eval/*.py             scripts de evaluación
eval/results/         ejecuciones reales de la evaluación (v1 y v2)
```

## Seguridad, en una línea por control

- Base de datos abierta en solo lectura (`mode=ro`).
- Autorizador de SQLite: solo lecturas; deniega `technicians.email` y `technicians.phone`, también en `WHERE`.
- El SQL del LLM y el código del sistema usan conexiones distintas.
- Una sentencia por llamada, máximo 100 filas, máximo 5 segundos.
- Las filas de ejemplo que ve el modelo no incluyen columnas bloqueadas.
- Sin claves en el código ni en el repositorio.
