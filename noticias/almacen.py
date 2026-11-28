"""
Dónde se guardan los titulares: un archivo por mes en datos/noticias/AAAA-MM.jsonl.

Antes era un solo archivo, pero creció hasta pasar el límite de 100 MB por archivo de GitHub.
Separado por mes, cada archivo queda bastante por debajo de ese límite.
"""
import json
import os
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(AQUI, "datos", "noticias")


def ruta_mes(fecha):
    return os.path.join(CARPETA, time.strftime("%Y-%m", time.gmtime(fecha)) + ".jsonl")


def archivos():
    if not os.path.isdir(CARPETA):
        return []
    return sorted(os.path.join(CARPETA, n) for n in os.listdir(CARPETA) if n.endswith(".jsonl"))


def leer_archivo(ruta):
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def leer(desde=None):
    """Todos los titulares, o solo los de los meses que pueden tener fechas >= desde."""
    salida = []
    for ruta in archivos():
        if desde is not None and os.path.basename(ruta)[:7] < time.strftime("%Y-%m", time.gmtime(desde)):
            continue
        salida.extend(leer_archivo(ruta))
    return salida


def reescribir(ruta, noticias):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for n in noticias:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    os.replace(tmp, ruta)
