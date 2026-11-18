"""Comprueba la conexión con el proveedor del LLM, sin mostrar la clave.

Uso:  python check_llm.py
"""
import os

from dotenv import load_dotenv
from openai import APIError, OpenAI

load_dotenv()
base = os.environ["LLM_BASE_URL"]
model = os.environ["LLM_MODEL"]
client = OpenAI(api_key=os.environ["LLM_API_KEY"], base_url=base, max_retries=0)  # sin reintentos: queremos ver el error


def explain(exc: Exception) -> str:
    """Código, servidor que responde y cuerpo del error: ayudan a saber si falla el proveedor o la red."""
    resp = getattr(exc, "response", None)
    detail = f" | servidor: {resp.headers.get('server')} | cuerpo: {resp.text[:200]!r}" if resp is not None else ""
    return f"{type(exc).__name__} {getattr(exc, 'status_code', '') or ''}{detail} | {str(exc)[:200]}"


print(f"1) Listar modelos en {base}")
try:
    ids = [m.id for m in client.models.list()]
    print("   OK. Modelos con 'flash' o 'gemma':", ", ".join(i for i in ids if "flash" in i or "gemma" in i) or ids[:30])
except APIError as exc:
    print("   Error:", explain(exc))

print(f"2) Llamada sencilla al modelo {model}")
try:
    resp = client.chat.completions.create(model=model, messages=[{"role": "user", "content": "Responde solo: OK"}])
    print(f"   Respuesta: {resp.choices[0].message.content!r}")
except APIError as exc:
    print("   Error:", explain(exc))
