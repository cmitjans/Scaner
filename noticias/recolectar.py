#!/usr/bin/env python3
"""
Recolecta titulares de 28 medios en español de América, Europa, Medio Oriente y Asia a través de sus RSS.

Los RSS son listados que los medios publican para que otros programas los lean, así que no hace falta
entrar a sus sitios. Para los medios sin RSS propio se usa el RSS de Google News filtrado por sitio
(trae solo titulares). No se guardan artículos completos: solo título, un resumen corto, fecha y enlace.

Uso: python3 recolectar.py   → agrega las noticias nuevas a datos/noticias.jsonl
"""
import calendar
import html
import json
import os
import re
import time
import urllib.request

import feedparser

AQUI = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(AQUI, "datos", "noticias.jsonl")
AGENTE = "Mozilla/5.0 (compatible; comparador-de-titulares/1.0; github.com/cmitjans/Scaner)"


def google(sitio):
    return f"https://news.google.com/rss/search?q=site:{sitio}+when:2d&hl=es-419&gl=CL&ceid=CL:es-419"


# medio, país de origen, tipo, url del RSS (o lista de urls: se usa la primera que funcione)
MEDIOS = [
    ("La Tercera", "Chile", "Privado", "https://www.latercera.com/arc/outboundfeeds/rss/?outputType=xml"),
    ("El Mostrador", "Chile", "Privado", google("elmostrador.cl")),
    ("BioBioChile", "Chile", "Privado", google("biobiochile.cl")),
    ("CIPER", "Chile", "Independiente", "https://www.ciperchile.cl/feed/"),
    ("El Ciudadano", "Chile", "Independiente", "https://www.elciudadano.com/feed/"),
    ("El País", "España", "Privado", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
    ("Infobae", "Argentina", "Privado", "https://www.infobae.com/arc/outboundfeeds/rss/"),
    ("CNN en Español", "EE. UU.", "Privado", google("cnnespanol.cnn.com")),
    ("Voz de América", "EE. UU.", "Estatal", google("vozdeamerica.com")),
    ("BBC Mundo", "Reino Unido", "Público", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("DW", "Alemania", "Público", "https://rss.dw.com/rdf/rss-sp-all"),
    ("France 24", "Francia", "Público", "https://www.france24.com/es/rss"),
    ("RT en español", "Rusia", "Estatal", ["https://actualidad.rt.com/feeds/all.rss", google("actualidad.rt.com")]),
    ("Xinhua", "China", "Estatal", google("spanish.news.cn")),
    ("CGTN", "China", "Estatal", google("espanol.cgtn.com")),
    ("TeleSUR", "Venezuela", "Estatal", google("telesurtv.net")),
    ("Prensa Latina", "Cuba", "Estatal", ["https://www.prensa-latina.cu/feed/", google("prensa-latina.cu")]),
    ("Sputnik Mundo", "Rusia", "Estatal", ["https://noticiaslatam.lat/export/rss2/archive/index.xml", google("noticiaslatam.lat")]),
    ("Anadolu", "Turquía", "Estatal", ["https://www.aa.com.tr/es/rss/default?cat=guncel", google("aa.com.tr/es")]),
    ("TRT Español", "Turquía", "Público", google("trtespanol.com")),
    ("HispanTV", "Irán", "Estatal", google("hispantv.com")),
    ("Pars Today", "Irán", "Estatal", google("parstoday.ir/es")),
    ("Al Mayadeen", "Líbano", "Privado", google("espanol.almayadeen.net")),
    ("Aurora", "Israel", "Privado", google("aurora-israel.co.il")),
    ("Pueblo en Línea", "China", "Estatal", google("spanish.peopledaily.com.cn")),
    ("NHK World", "Japón", "Público", google("www3.nhk.or.jp/nhkworld/es")),
    ("Yonhap", "Corea del Sur", "Agencia", google("sp.yna.co.kr")),
    ("KBS World", "Corea del Sur", "Público", google("world.kbs.co.kr")),
]


def limpiar(texto):
    texto = html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))
    return re.sub(r"\s+", " ", texto).strip()


def leer(medio, url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    datos = urllib.request.urlopen(req, timeout=30).read()
    salida = []
    for e in feedparser.parse(datos).entries:
        titulo = limpiar(e.get("title"))
        if "news.google.com" in url:
            titulo = re.sub(r"\s+-\s+[^-]+$", "", titulo)  # Google agrega " - Nombre del medio"
            resumen = ""
        else:
            resumen = limpiar(e.get("summary"))[:280]
        if not titulo:
            continue
        t = e.get("published_parsed") or e.get("updated_parsed")
        fecha = int(calendar.timegm(t)) if t else int(time.time())
        if fecha < time.time() - 7 * 86400:
            continue  # algunos RSS incluyen notas antiguas; solo interesan las recientes
        salida.append({"medio": medio, "titulo": titulo, "resumen": resumen,
                       "fecha": fecha, "enlace": e.get("link", "")})
    return salida


def main():
    os.makedirs(os.path.dirname(ARCHIVO), exist_ok=True)
    vistos = set()
    if os.path.exists(ARCHIVO):
        with open(ARCHIVO, encoding="utf-8") as f:
            for linea in f:
                n = json.loads(linea)
                vistos.add((n["medio"], n["titulo"].lower()))
    nuevas = 0
    with open(ARCHIVO, "a", encoding="utf-8") as f:
        for medio, pais, tipo, urls in MEDIOS:
            items = None
            for url in (urls if isinstance(urls, list) else [urls]):
                try:
                    items = leer(medio, url)
                    break
                except Exception as e:
                    print(f"  {medio}: no se pudo leer {url[:50]} ({e.__class__.__name__})")
            if items is None:
                continue
            n = 0
            for it in items:
                clave = (medio, it["titulo"].lower())
                if clave in vistos:
                    continue
                vistos.add(clave)
                it.update({"pais": pais, "tipo": tipo})
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
            nuevas += n
            print(f"  {medio}: {n} nuevas de {len(items)}")
    print(f"Total nuevas: {nuevas}")


if __name__ == "__main__":
    main()
