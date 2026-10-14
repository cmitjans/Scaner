#!/usr/bin/env python3
"""
Radiografía de la web: toma una muestra aleatoria de páginas de Common Crawl y la resume.

Common Crawl (commoncrawl.org) rastrea la web pública cada mes y publica el resultado gratis.
Este script NO rastrea sitios por su cuenta: solo lee archivos que Common Crawl ya publicó.

Para cada página anota: dominio, idioma, tipo de sitio, rastreadores que carga, título y un fragmento.
Las páginas detectadas como contenido para adultos solo se cuentan; no se guarda su dirección ni su texto.

Uso: python3 radiografia.py [--archivos 3] [--por-archivo 3500] [--salida datos.json]
"""
import argparse
import gzip
import io
import json
import random
import re
import sys
import time
import urllib.request
from collections import Counter
from urllib.parse import urlsplit

import py3langid
from selectolax.lexbor import LexborHTMLParser as HTMLParser
from warcio.archiveiterator import ArchiveIterator

BASE = "https://data.commoncrawl.org/"
AGENTE = "Radiografia-web/1.0 (experimento personal; github.com/cmitjans/Scaner)"

# Rastreadores: texto que aparece en el HTML → empresa
RASTREADORES = {
    "google-analytics.com": "Google Analytics",
    "googletagmanager.com": "Google Tag Manager",
    "doubleclick.net": "Google Ads",
    "googlesyndication.com": "Google Ads",
    "googleadservices.com": "Google Ads",
    "connect.facebook.net": "Meta Pixel",
    "static.hotjar.com": "Hotjar",
    "clarity.ms": "Microsoft Clarity",
    "bat.bing.com": "Microsoft Ads",
    "analytics.tiktok.com": "TikTok Pixel",
    "snap.licdn.com": "LinkedIn Insight",
    "mc.yandex.ru": "Yandex Metrica",
    "static.criteo.net": "Criteo",
    "cdn.taboola.com": "Taboola",
    "outbrain.com": "Outbrain",
    "amazon-adsystem.com": "Amazon Ads",
    "scorecardresearch.com": "comScore",
    "quantserve.com": "Quantcast",
    "adnxs.com": "Xandr",
    "ct.pinterest.com": "Pinterest Tag",
    "static.ads-twitter.com": "X (Twitter) Ads",
    "static.cloudflareinsights.com": "Cloudflare Analytics",
    "cdn.segment.com": "Segment",
    "cdn.mxpnl.com": "Mixpanel",
    "js.hs-scripts.com": "HubSpot",
}

# Contenido para adultos: solo se cuenta y se oculta. Es un filtro amplio a propósito:
# prefiere ocultar de más que mostrar algo explícito.
ADULTO = re.compile(
    r"porn|xxx|xvideo|sexcam|webcam ?girl|escort|hentai|nsfw|onlyfans|camgirl|milf|erotic|erótic|"
    r"sexo|sexy|sex |nude|naked|desnud|putas?\b|puta |follando|cogiendo|"
    r"порн|секс|эроти|интим|"
    r"色情|成人|黄色|a片|av女|无码|無碼|中出|自拍|乱伦|性爱|做爱|约炮|裸|"
    r"アダルト|エロ|無修正|セックス|"
    r"casino|apuestas|bet365|slot gacor|judi",  # apuestas y casinos: también se ocultan de la galería
    re.I)

# La galería solo muestra páginas en estos idiomas, para poder filtrar con más confianza.
IDIOMAS_GALERIA = {"es", "en", "pt", "fr", "de", "it"}

TIENDA = re.compile(r"add to (cart|bag|basket)|añadir al carrito|agregar al carrito|comprar ahora|in den warenkorb|ajouter au panier|aggiungi al carrello|cdn\.shopify\.com|\"@type\"\s*:\s*\"Product\"", re.I)
FORO = re.compile(r"phpbb|vbulletin|xenforo|discourse|invision community|smf_|/forum|/foro|/viewtopic", re.I)
ESTACIONADO = re.compile(r"domain (is|may be) for sale|buy this domain|this domain is parked|dominio está a la venta|parked free", re.I)


def descargar(url, rango=None):
    req = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    if rango:
        req.add_header("Range", rango)
    return urllib.request.urlopen(req, timeout=120)


def ultimo_rastreo():
    with descargar("https://index.commoncrawl.org/collinfo.json") as r:
        return json.load(r)[0]["id"]


def lista_warc(rastreo):
    with descargar(f"{BASE}crawl-data/{rastreo}/warc.paths.gz") as r:
        return gzip.decompress(r.read()).decode().split()


def categoria(url, html, og_type, generator):
    u = url.lower()
    if ESTACIONADO.search(html[:20000]):
        return "Dominio en venta o estacionado"
    if TIENDA.search(html):
        return "Tienda"
    if FORO.search(u) or FORO.search(generator) or FORO.search(html[:5000]):
        return "Foro"
    if og_type == "article" and re.search(r"news|noticia|diario|periodico|zeitung|journal|nachrichten|press", u):
        return "Noticias"
    if og_type == "article" or "wordpress" in generator.lower() or "blogspot." in u or "/blog" in u:
        return "Blog o artículo"
    return "Otro"


def decodificar(cuerpo, ctype):
    """Usa la codificación que declara la página (muchas páginas chinas o rusas no usan UTF-8)."""
    m = re.search(r"charset=([\w-]+)", ctype or "", re.I) or \
        re.search(rb"<meta[^>]+charset=[\"']?([\w-]+)", cuerpo[:4000], re.I)
    cs = m.group(1) if m else "utf-8"
    if isinstance(cs, bytes):
        cs = cs.decode("ascii", "ignore")
    try:
        return cuerpo.decode(cs, errors="replace")
    except LookupError:
        return cuerpo.decode("utf-8", errors="replace")


def analizar(url, cuerpo, ctype=""):
    html = decodificar(cuerpo, ctype)
    arbol = HTMLParser(html)
    titulo = (arbol.css_first("title").text(strip=True) if arbol.css_first("title") else "")[:160]

    def meta(selector, attr="content"):
        n = arbol.css_first(selector)
        return (n.attributes.get(attr) or "").strip() if n else ""

    descripcion = meta('meta[name="description"]')
    og_type = meta('meta[property="og:type"]').lower()
    generator = meta('meta[name="generator"]')
    for tag in arbol.css("script, style, noscript, nav, header, footer"):
        tag.decompose()
    cuerpo_txt = arbol.body.text(separator=" ", strip=True) if arbol.body else ""
    texto = re.sub(r"\s+", " ", cuerpo_txt)
    palabras = len(texto.split())

    muestra = (titulo + " " + descripcion + " " + texto[:1500]).strip()
    idioma = py3langid.classify(muestra)[0] if len(muestra) > 20 else "?"

    host = (urlsplit(url).hostname or "").lower()
    partes = host.split(".")
    tld = partes[-1] if len(partes) > 1 else ""
    dominio = ".".join(partes[-2:]) if len(partes) >= 2 else host

    rastreadores = sorted({v for k, v in RASTREADORES.items() if k in html})
    adulto = bool(ADULTO.search(titulo + " " + descripcion + " " + host + " " + texto[:3000]))

    fila = {
        "tld": tld,
        "idioma": idioma,
        "tipo": "Contenido para adultos" if adulto else categoria(url, html, og_type, generator),
        "rastreadores": rastreadores,
        "palabras": palabras,
        "adulto": adulto,
    }
    if not adulto and idioma in IDIOMAS_GALERIA:
        fragmento = descripcion or texto[:400]
        fila.update({
            "dominio": dominio,
            "url": url,
            "titulo": titulo,
            "fragmento": fragmento[:240],
        })
    return fila


def tamano(ruta):
    for intento in range(4):
        try:
            req = urllib.request.Request(BASE + ruta, method="HEAD", headers={"User-Agent": AGENTE})
            with urllib.request.urlopen(req, timeout=60) as r:
                return int(r.headers["Content-Length"])
        except Exception:
            time.sleep(3 * (intento + 1))
    return 0


def registros_en(trozo, maximo):
    """Busca el inicio de un registro WARC dentro de un trozo y lee los siguientes."""
    pos = 0
    while True:
        pos = trozo.find(b"\x1f\x8b\x08", pos)
        if pos < 0:
            return
        try:
            n = 0
            for reg in ArchiveIterator(io.BytesIO(trozo[pos:])):
                yield reg
                n += 1
                if n >= maximo:
                    return
            return
        except Exception:
            pos += 3  # no era el inicio de un registro; sigue buscando


def leer_archivo(ruta, maximo, rnd, por_salto=5, bloque=1_000_000):
    """Lee páginas desde puntos al azar del archivo (dentro, las páginas están ordenadas por dominio)."""
    filas = []
    total = tamano(ruta)
    if not total:
        return filas
    saltos = max(1, maximo // por_salto)
    for inicio in sorted(rnd.randrange(0, max(1, total - bloque)) for _ in range(saltos)):
        trozo = None
        for intento in range(4):  # Common Crawl a veces corta conexiones o pide ir más lento
            try:
                with descargar(BASE + ruta, f"bytes={inicio}-{inicio + bloque - 1}") as r:
                    trozo = r.read()
                break
            except Exception as e:
                print(f"  reintento {intento + 1} ({e.__class__.__name__})", file=sys.stderr)
                time.sleep(3 * (intento + 1))
        if trozo is None:
            continue
        tomadas = 0
        try:
            for reg in registros_en(trozo, por_salto * 6):
                if reg.rec_type != "response" or not reg.http_headers:
                    continue
                ctype = (reg.http_headers.get_header("Content-Type") or "").lower()
                if "text/html" not in ctype or reg.http_headers.get_statuscode() != "200":
                    continue
                url = reg.rec_headers.get_header("WARC-Target-URI")
                try:
                    filas.append(analizar(url, reg.content_stream().read(1_500_000), ctype))
                    tomadas += 1
                except Exception as e:
                    print("  error en", url, e, file=sys.stderr)
                if tomadas >= por_salto:
                    break
        except Exception:
            pass  # el trozo terminó a mitad de un registro
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--archivos", type=int, default=3)
    ap.add_argument("--por-archivo", type=int, default=3500)
    ap.add_argument("--salida", default="datos.json")
    ap.add_argument("--rastreo", default=None)
    ap.add_argument("--semilla", type=int, default=None)
    a = ap.parse_args()

    rastreo = a.rastreo or ultimo_rastreo()
    rutas = lista_warc(rastreo)
    rnd = random.Random(a.semilla)
    elegidas = rnd.sample(rutas, a.archivos)
    print(f"Rastreo {rastreo}: {len(rutas)} archivos; se leen {a.archivos} al azar", file=sys.stderr)

    filas = []
    for i, ruta in enumerate(elegidas, 1):
        t = time.time()
        nuevas = leer_archivo(ruta, a.por_archivo, rnd)
        filas += nuevas
        print(f"  {i}/{len(elegidas)} {ruta.split('/')[-1]}: {len(nuevas)} páginas en {time.time()-t:.0f}s", file=sys.stderr)

    resumen = {
        "rastreo": rastreo,
        "archivos": [r.split("/")[-1] for r in elegidas],
        "fecha": time.strftime("%Y-%m-%d"),
        "total": len(filas),
        "adulto": sum(f["adulto"] for f in filas),
        "idiomas": Counter(f["idioma"] for f in filas).most_common(),
        "tlds": Counter(f["tld"] for f in filas).most_common(40),
        "tipos": Counter(f["tipo"] for f in filas).most_common(),
        "rastreadores": Counter(r for f in filas for r in f["rastreadores"]).most_common(),
        "con_rastreadores": sum(1 for f in filas if f["rastreadores"]),
        "dominios_repetidos": Counter(f["dominio"] for f in filas if "dominio" in f).most_common(15),
    }
    galeria = [
        {k: f[k] for k in ("dominio", "url", "titulo", "fragmento", "idioma", "tipo", "rastreadores")}
        for f in filas if not f["adulto"] and f.get("titulo") and f["idioma"] in IDIOMAS_GALERIA
        and "\ufffd" not in f["titulo"]
    ]
    with open(a.salida, "w", encoding="utf-8") as fh:
        json.dump({"resumen": resumen, "galeria": galeria}, fh, ensure_ascii=False)
    print(f"Listo: {len(filas)} páginas → {a.salida}", file=sys.stderr)


if __name__ == "__main__":
    main()
