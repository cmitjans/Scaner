#!/usr/bin/env python3
"""
Traduce al español los titulares en otros idiomas, en esta misma máquina, con Argos Translate.

No se envía nada a servicios externos: los modelos de traducción se descargan una vez y corren aquí.
Argos no tiene modelos directos de ruso, chino, árabe o francés al español, así que traduce pasando
por el inglés (ruso → inglés → español). Eso agrega errores, sobre todo en chino y árabe: la traducción sirve para entender y
comparar, pero el titular original siempre se guarda y se muestra al lado.

Uso: python3 traducir.py   → agrega "titulo_es" a los titulares de datos/noticias.jsonl que no lo tengan
"""
import json
import os
import re
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(AQUI, "datos", "noticias.jsonl")
IDIOMAS = ["en", "fr", "ru", "zh", "ar"]
MAXIMO = 4000  # tope por ejecución; lo que falte se traduce en la siguiente


def preparar():
    """Descarga los modelos que falten (idioma → inglés y inglés → español)."""
    import argostranslate.package as P
    import argostranslate.translate as T
    necesarios = {(i, "en") for i in IDIOMAS if i != "en"} | {("en", "es")}
    instalados = {(p.from_code, p.to_code) for p in P.get_installed_packages()}
    faltan = necesarios - instalados
    if faltan:
        P.update_package_index()
        for p in P.get_available_packages():
            if (p.from_code, p.to_code) in faltan:
                print(f"  descargando modelo {p.from_code}→{p.to_code}")
                P.install_from_path(p.download())
    al_ingles = {i: T.get_translation_from_codes(i, "en") for i in IDIOMAS if i != "en"}
    al_espanol = T.get_translation_from_codes("en", "es")

    def traducir(texto, idioma):
        if mayusculas(texto):
            texto = texto[:1] + texto[1:].lower()  # "PUTIN SAYS..." confunde al modelo
        ingles = texto if idioma == "en" else al_ingles[idioma].translate(texto).strip()
        es = al_espanol.translate(ingles).strip()
        if parece_ingles(es):
            # Con titulares en Mayúscula Inicial el modelo a veces copia el texto sin traducir;
            # se reintenta con mayúsculas normales de oración.
            es = al_espanol.translate(oracion(ingles)).strip()
        return es
    return traducir


INGLES = re.compile(r"\b(the|of|and|with|for|is|are|has|have|was|were|after|over|from|says)\b", re.I)


def parece_ingles(texto):
    return len(INGLES.findall(texto)) >= 2


def mayusculas(texto):
    letras = [c for c in texto if c.isalpha()]
    return len(letras) > 10 and sum(c.isupper() for c in letras) > 0.7 * len(letras)


def oracion(texto):
    """'Global Poverty Reduction Reporter' → 'Global poverty reduction reporter' (respeta siglas)."""
    palabras = texto.split(" ")
    return " ".join([palabras[0]] + [w if w.isupper() else w[:1].lower() + w[1:] for w in palabras[1:]])


def main():
    with open(ARCHIVO, encoding="utf-8") as f:
        noticias = [json.loads(l) for l in f]
    pendientes = [n for n in noticias if n.get("idioma", "es") != "es" and "titulo_es" not in n]
    print(f"{len(pendientes)} titulares por traducir")
    if not pendientes:
        return
    traducir = preparar()
    t0, hechos = time.time(), 0
    for n in pendientes[:MAXIMO]:
        try:
            n["titulo_es"] = traducir(n["titulo"], n["idioma"])
            hechos += 1
        except Exception as e:
            print(f"  no se pudo traducir ({e.__class__.__name__}): {n['titulo'][:60]}")
    print(f"{hechos} traducidos en {time.time() - t0:.0f} s")
    tmp = ARCHIVO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for n in noticias:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    os.replace(tmp, ARCHIVO)


if __name__ == "__main__":
    main()
