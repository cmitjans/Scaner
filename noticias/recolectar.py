#!/usr/bin/env python3
"""
Recolecta titulares de medios en seis idiomas (español, inglés, francés, ruso, chino y árabe) a través de sus RSS.

Los RSS son listados que los medios publican para que otros programas los lean, así que no hace falta
entrar a sus sitios. Para los medios sin RSS propio se usa el RSS de Google News filtrado por sitio
(trae solo titulares). Los titulares en otros idiomas se traducen después con traducir.py. No se guardan artículos completos: solo título, un resumen corto, fecha y enlace.

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


# Edición de Google News que corresponde a cada idioma
EDICION = {"es": "hl=es-419&gl=CL&ceid=CL:es-419", "en": "hl=en-US&gl=US&ceid=US:en", "fr": "hl=fr&gl=FR&ceid=FR:fr",
           "ru": "hl=ru&gl=RU&ceid=RU:ru", "zh": "hl=zh-CN&gl=CN&ceid=CN:zh-Hans", "zht": "hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
           "ar": "hl=ar&gl=EG&ceid=EG:ar"}


def google(sitio, idioma="es"):
    return f"https://news.google.com/rss/search?q=site:{sitio}+when:2d&{EDICION[idioma]}"


# medio, país de origen, tipo, url del RSS (o lista de urls: se usa la primera que funcione)
ESPANOL = [
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

# Medios en otros idiomas: medio, país, tipo, idioma, url(s). Se eligieron por ser influyentes en su idioma,
# no por tener también edición en español. "familia" agrupa ediciones del mismo medio en distintos idiomas.
OTROS = [
    # Inglés
    ("BBC News", "Reino Unido", "Público", "en", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian", "Reino Unido", "Privado", "en", "https://www.theguardian.com/world/rss"),
    ("Fox News", "EE. UU.", "Privado", "en", ["https://moxie.foxnews.com/google-publisher/world.xml", google("foxnews.com", "en")]),
    ("The New York Times", "EE. UU.", "Privado", "en", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("AP", "EE. UU.", "Agencia", "en", google("apnews.com", "en")),
    ("Al Jazeera English", "Catar", "Estatal", "en", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("RT", "Rusia", "Estatal", "en", ["https://www.rt.com/rss/news/", google("rt.com", "en")]),
    ("TASS English", "Rusia", "Estatal", "en", ["https://tass.com/rss/v2.xml", google("tass.com", "en")]),
    ("CGTN English", "China", "Estatal", "en", google("news.cgtn.com", "en")),
    ("Global Times", "China", "Estatal", "en", ["https://www.globaltimes.cn/rss/outbrain.xml", google("globaltimes.cn", "en")]),
    ("Times of India", "India", "Privado", "en", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"),
    ("Dawn", "Pakistán", "Privado", "en", ["https://www.dawn.com/feeds/world", google("dawn.com", "en")]),
    # Francés
    ("Le Monde", "Francia", "Privado", "fr", "https://www.lemonde.fr/international/rss_full.xml"),
    ("Le Figaro", "Francia", "Privado", "fr", "https://www.lefigaro.fr/rss/figaro_international.xml"),
    ("France 24 (francés)", "Francia", "Público", "fr", "https://www.france24.com/fr/rss"),
    ("RFI", "Francia", "Público", "fr", ["https://www.rfi.fr/fr/rss", google("rfi.fr/fr", "fr")]),
    ("Jeune Afrique", "Francia", "Privado", "fr", ["https://www.jeuneafrique.com/feed/", google("jeuneafrique.com", "fr")]),
    # Ruso
    ("TASS", "Rusia", "Estatal", "ru", ["https://tass.ru/rss/v2.xml", google("tass.ru", "ru")]),
    ("RIA Novosti", "Rusia", "Estatal", "ru", ["https://ria.ru/export/rss2/archive/index.xml", google("ria.ru", "ru")]),
    ("Meduza", "Letonia (exilio ruso)", "Independiente", "ru", ["https://meduza.io/rss/all", google("meduza.io", "ru")]),
    ("Novaya Gazeta Europe", "Letonia (exilio ruso)", "Independiente", "ru", ["https://novayagazeta.eu/feed/rss", google("novayagazeta.eu", "ru")]),
    ("BBC Russian", "Reino Unido", "Público", "ru", "https://feeds.bbci.co.uk/russian/rss.xml"),
    # Chino
    ("Xinhua (chino)", "China", "Estatal", "zh", [google("xinhuanet.com", "zh"), google("news.cn", "zh")]),
    ("Diario del Pueblo (chino)", "China", "Estatal", "zh", google("people.com.cn", "zh")),
    ("Huanqiu", "China", "Estatal", "zh", google("huanqiu.com", "zh")),
    ("Lianhe Zaobao", "Singapur", "Privado", "zh", [google("zaobao.com.sg", "zh"), google("zaobao.com", "zh")]),
    ("CNA Taiwán", "Taiwán", "Agencia", "zh", ["https://feeds.feedburner.com/rsscna/intworld", google("cna.com.tw", "zht")]),
    ("BBC Chinese", "Reino Unido", "Público", "zh", "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"),
    # Árabe
    ("Al Jazeera (árabe)", "Catar", "Estatal", "ar", ["https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9", google("aljazeera.net", "ar")]),
    ("Al Arabiya", "Arabia Saudita", "Privado", "ar", ["https://www.alarabiya.net/feed/rss2/ar.xml", google("alarabiya.net", "ar")]),
    ("Asharq Al-Awsat", "Arabia Saudita", "Privado", "ar", google("aawsat.com", "ar")),
    ("Sky News Arabia", "Emiratos Árabes", "Privado", "ar", google("skynewsarabia.com", "ar")),
    ("Al Mayadeen (árabe)", "Líbano", "Privado", "ar", google("almayadeen.net", "ar")),
    ("RT Arabic", "Rusia", "Estatal", "ar", google("arabic.rt.com", "ar")),
    ("BBC Arabic", "Reino Unido", "Público", "ar", "https://feeds.bbci.co.uk/arabic/rss.xml"),
]
MEDIOS = [(m, p, t, "es", u) for m, p, t, u in ESPANOL] + OTROS

# Ediciones del mismo medio en distintos idiomas
FAMILIAS = {
    "BBC": ["BBC Mundo", "BBC News", "BBC Russian", "BBC Chinese", "BBC Arabic"],
    "RT": ["RT en español", "RT", "RT Arabic"],
    "Al Jazeera": ["Al Jazeera English", "Al Jazeera (árabe)"],
    "France 24": ["France 24", "France 24 (francés)"],
    "CGTN": ["CGTN", "CGTN English"],
    "Xinhua": ["Xinhua", "Xinhua (chino)"],
    "Diario del Pueblo": ["Pueblo en Línea", "Diario del Pueblo (chino)"],
    "TASS": ["TASS English", "TASS"],
    "Al Mayadeen": ["Al Mayadeen", "Al Mayadeen (árabe)"],
}
FAMILIA_DE = {m: f for f, ms in FAMILIAS.items() for m in ms}


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
        for medio, pais, tipo, idioma, urls in MEDIOS:
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
                it.update({"pais": pais, "tipo": tipo, "idioma": idioma})
                if medio in FAMILIA_DE:
                    it["familia"] = FAMILIA_DE[medio]
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
                n += 1
            nuevas += n
            print(f"  {medio}: {n} nuevas de {len(items)}")
    print(f"Total nuevas: {nuevas}")


if __name__ == "__main__":
    main()
