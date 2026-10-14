#!/usr/bin/env python3
"""
Arma noticias/index.html a partir de plantilla.html y datos/analisis.json.
GitHub Actions lo corre después de cada análisis, así la página publicada en GitHub Pages
siempre muestra los datos más recientes.
"""
import json
import os

from analizar import NEGATIVAS, POSITIVAS

AQUI = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(AQUI, "datos", "analisis.json"), encoding="utf-8") as f:
        datos = f.read().replace("�", "").replace("</", "<\\/")
    with open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8") as f:
        html = f.read()
    html = (html.replace("__DATA__", datos)
                .replace("__NEG__", json.dumps(sorted(NEGATIVAS)))
                .replace("__POS__", json.dumps(sorted(POSITIVAS))))
    with open(os.path.join(AQUI, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html: {len(html) // 1024} KB")


if __name__ == "__main__":
    main()
