#!/usr/bin/env python3
"""
Analiza los titulares recolectados y busca diferencias entre medios.

Mide cuatro cosas, con reglas definidas de antemano (ver las listas más abajo):
1. Agenda: qué países y temas aparecen más en cada medio.
2. Tono: si los titulares que mencionan a un país usan más palabras negativas o positivas.
3. Elección de palabras: pares como "régimen" / "gobierno" o "ataque" / "operación".
4. Misma noticia, distintos titulares: agrupa titulares sobre el mismo hecho para compararlos.

Los titulares en inglés, francés, ruso, chino y árabe se analizan a partir de su traducción automática
al español (traducir.py), así que esas mediciones son todavía más aproximadas; la agenda (qué países se
nombran) es la más confiable, porque los nombres de países se traducen bien.
Además de por medio, todo se resume por idioma y por "familia" (un mismo medio en varios idiomas).

Todo es aproximado: se basa en palabras de los titulares, no en leer los artículos.
Uso: python3 analizar.py   → escribe datos/analisis.json
"""
import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict

from recolectar import FAMILIA_DE

AQUI = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(AQUI, "datos", "noticias.jsonl")
SALIDA = os.path.join(AQUI, "datos", "analisis.json")


def norm(t):
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# --- 1. Países y actores (patrones sobre texto normalizado, sin tildes) ---
PAISES = {
    "EE. UU.": r"\b(ee\.? ?uu\.?|eeuu|estados unidos|washington|casa blanca|trump|estadounidense|norteamerican\w*|pentagono)\b",
    "China": r"\b(china|chino|china|beijing|pekin|xi jinping|chinos|chinas)\b",
    "Rusia": r"\b(rusia|ruso|rusa|rusos|kremlin|moscu|putin)\b",
    "Ucrania": r"\b(ucrania|ucraniano\w*|kiev|kyiv|zelenski\w*)\b",
    "Israel": r"\b(israel|israeli\w*|netanyahu|tel aviv)\b",
    "Palestina": r"\b(palestin\w*|gaza|cisjordania|hamas)\b",
    "Irán": r"\b(iran|irani\w*|teheran)\b",
    "Venezuela": r"\b(venezuela|venezolan\w*|caracas|maduro)\b",
    "Cuba": r"\b(cuba|cuban\w*|la habana)\b",
    "Unión Europea": r"\b(union europea|bruselas|comision europea)\b",
    "Corea del Norte": r"\b(corea del norte|norcorean\w*|pyongyang|kim jong[ -]?un)\b",
    "Corea del Sur": r"\b(corea del sur|surcorean\w*|seul)\b",
    "Japón": r"\b(japon|japones\w*|tokio)\b",
    "Turquía": r"\b(turquia|turco|turca|turcos|ankara|erdogan)\b",
    "India": r"\b(india|nueva delhi|modi)\b",
    "Líbano": r"\b(libano|libanes\w*|beirut|hezbol\w*)\b",
    "Chile": r"\b(chile|chilen\w*|santiago de chile|la moneda)\b",
    "Argentina": r"\b(argentin\w*|buenos aires|milei)\b",
    "Brasil": r"\b(brasil\w*|lula|bolsonaro)\b",
    "México": r"\b(mexico|mexican\w*|sheinbaum)\b",
}
PAISES = {k: re.compile(v) for k, v in PAISES.items()}
# Expresiones que contienen el nombre de un país pero no hablan de él
FALSOS = re.compile(r"montana rusa|ruleta rusa|ensalad\w* rusa|tortilla espanola|gripe espanola|papa(s)? francesa(s)?|india (yanomami|mapuche)|pueblos? indio\w*")

# --- 2. Tono: listas cortas de palabras claramente negativas o positivas en titulares ---
NEGATIVAS = set("""ataque ataques ataca atacan amenaza amenazas amenazan crisis condena condenan conflicto guerra muerte
muertes muertos mueren asesinato asesinan escandalo caos fracaso fracasa acusa acusan acusado acusacion denuncia denuncian
represion reprime agresion agresiones violencia violento tension tensiones colapso derrumbe sancion sanciones castigo
bloqueo injerencia provocacion corrupcion fraude ilegal dictadura regimen terror terrorista terroristas bombardeo
bombardea bombardeos invasion masacre victimas destruye destruccion rechaza rechazo critica criticas polemica peligro
derrota hostil hostilidad espionaje espia propaganda desinformacion""".split())
POSITIVAS = set("""acuerdo acuerdos coopera cooperacion alianza exito exitoso logra logro logros avance avances avanza
crecimiento crece record historico celebra celebran ayuda apoyo apoya paz dialogo desarrollo progreso innovacion
fortalece fortalecer amistad beneficio beneficios mejora mejoran gana ganan victoria impulsa impulso prospera prosperidad
solidaridad estabilidad recupera recuperacion inaugura""".split())

# --- 3. Elección de palabras: grupos de términos que describen cosas parecidas con distinta carga ---
PARES = [
    ("régimen", r"\bregimen\b", "gobierno", r"\bgobierno\b"),
    ("dictador", r"\bdictador\w*", "presidente / mandatario", r"\b(presidente|mandatario)\b"),
    ("terrorista(s)", r"\bterrorist\w*", "militante(s) / milicia(s)", r"\b(militante\w*|milicia\w*|combatiente\w*|insurgente\w*)\b"),
    ("invasión", r"\binvasion\b", "operación militar", r"\boperacion (militar|especial)\w*"),
    ("ataque(s)", r"\bataque\w*", "ofensiva / operación", r"\b(ofensiva\w*|operacion\w*)\b"),
    ("bloqueo", r"\bbloqueo\b", "embargo / sanciones", r"\b(embargo|sancion\w*)\b"),
    ("genocidio", r"\bgenocid\w*", "guerra / conflicto", r"\b(guerra|conflicto)\b"),
    ("ilegales", r"\bilegales\b", "migrantes", r"\b(migrante\w*|inmigrante\w*)\b"),
]
PARES = [(a, re.compile(pa), b, re.compile(pb)) for a, pa, b, pb in PARES]

STOP = set(norm(w) for w in """a al algo ante antes como con contra cual cuando de del desde donde dos e el ella ellos en entre
era es esa ese eso esta este esto estos fue fueron ha han hasta hay la las le les lo los mas me mi mientras muy nada ni no
nos o otra otro para pero por porque que quien se sea segun ser si sin sobre son su sus tambien te tiene tienen todo tras
tu un una uno unos y ya mas ano anos dia dias nuevo nueva hoy ayer video videos foto fotos asi cada vez puede pueden
dice dicen podria tras tres""".split())


def palabras(t):
    return [w for w in re.findall(r"[a-zñ0-9]+", norm(t)) if len(w) > 2 and w not in STOP]


def tono(texto_norm):
    ws = re.findall(r"[a-zñ]+", texto_norm)
    neg = sum(w in NEGATIVAS for w in ws)
    pos = sum(w in POSITIVAS for w in ws)
    return pos - neg, neg, pos


def agrupar(noticias, umbral=0.32, ventana=3 * 86400):
    """Agrupa titulares sobre el mismo hecho comparando sus palabras (TF-IDF + coseno)."""
    docs = [Counter(palabras(n["titulo"] + " " + n["resumen"][:160])) for n in noticias]
    df = Counter(w for d in docs for w in d)
    N = len(docs)
    vecs = []
    for d in docs:
        v = {w: c * math.log(N / df[w]) for w, c in d.items() if df[w] > 1}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1
        vecs.append({w: x / norma for w, x in v.items()})
    orden = sorted(range(N), key=lambda i: noticias[i]["fecha"])
    grupos = []  # cada grupo: {"items": [...], "centro": {}, "fecha": t}
    for i in orden:
        v = vecs[i]
        if not v:
            continue
        mejor, sim_mejor = None, umbral
        for g in grupos[-400:]:
            if abs(noticias[i]["fecha"] - g["fecha"]) > ventana:
                continue
            sim = sum(x * g["centro"].get(w, 0) for w, x in v.items())
            if sim > sim_mejor:
                mejor, sim_mejor = g, sim
        if mejor is None:
            grupos.append({"items": [i], "centro": dict(v), "fecha": noticias[i]["fecha"]})
        else:
            mejor["items"].append(i)
            k = len(mejor["items"])
            c = mejor["centro"]
            for w in set(c) | set(v):
                c[w] = (c.get(w, 0) * (k - 1) + v.get(w, 0)) / k
    return grupos


def main():
    noticias = []
    with open(ENTRADA, encoding="utf-8") as f:
        for linea in f:
            n = json.loads(linea)
            n.setdefault("idioma", "es")
            if n["idioma"] != "es":
                if "titulo_es" not in n:
                    continue  # todavía sin traducir
                n["original"], n["titulo"] = n["titulo"], n["titulo_es"]
                n["resumen"] = ""  # los resúmenes no se traducen
            noticias.append(n)
    medios = sorted({n["medio"] for n in noticias})
    info = {n["medio"]: {"pais": n["pais"], "tipo": n["tipo"], "idioma": n["idioma"],
                         **({"familia": FAMILIA_DE[n["medio"]]} if n["medio"] in FAMILIA_DE else {})}
            for n in noticias}
    por_medio = Counter(n["medio"] for n in noticias)

    indice = []                              # cada titular con lo que se detectó en él (para la página)
    agenda = defaultdict(Counter)            # medio → país → titulares
    tono_suma = defaultdict(lambda: defaultdict(list))  # medio → país → [tono]
    uso_pares = defaultdict(lambda: defaultdict(Counter))  # par → medio → {a, b}
    for n in noticias:
        t = norm(n["titulo"] + " " + n["resumen"])
        t = FALSOS.sub(" ", t)  # "montaña rusa" no es Rusia
        tt = norm(n["titulo"])
        sc, _, _ = tono(t)
        paises_n = []
        for pais, rx in PAISES.items():
            if rx.search(t):
                agenda[n["medio"]][pais] += 1
                tono_suma[n["medio"]][pais].append(sc)
                paises_n.append(pais)
        terminos = []
        for a, ra, b, rb in PARES:
            if ra.search(tt):
                uso_pares[a][n["medio"]]["a"] += 1
                terminos.append(a + "|a")
            if rb.search(tt):
                uso_pares[a][n["medio"]]["b"] += 1
                terminos.append(a + "|b")
        x = {"m": n["medio"], "t": n["titulo"], "e": n["enlace"], "f": n["fecha"],
             "p": paises_n, "s": sc, "w": terminos}
        if "original" in n:
            x["o"] = n["original"]
        indice.append(x)

    agenda_out = {m: {p: round(100 * agenda[m][p] / por_medio[m], 1) for p in PAISES} for m in medios}
    tono_out = {m: {p: {"media": round(sum(v) / len(v), 2), "n": len(v)}
                    for p, v in tono_suma[m].items() if len(v) >= 3} for m in medios}
    # Por idioma: promedio de los medios de ese idioma (cada medio pesa lo mismo, tenga 20 o 100 titulares)
    idiomas = sorted({info[m]["idioma"] for m in medios})
    agenda_idioma, tono_idioma = {}, {}
    for l in idiomas:
        ms = [m for m in medios if info[m]["idioma"] == l]
        agenda_idioma[l] = {p: round(sum(agenda_out[m][p] for m in ms) / len(ms), 1) for p in PAISES}
        tono_idioma[l] = {}
        for p in PAISES:
            v = [x for m in ms for x in tono_suma[m].get(p, [])]
            if len(v) >= 5:
                tono_idioma[l][p] = {"media": round(sum(v) / len(v), 2), "n": len(v)}

    pares_out = [{"a": a, "b": b, "medios": {m: dict(uso_pares[a][m]) for m in medios if uso_pares[a][m]}}
                 for a, _, b, _ in PARES]

    grupos = agrupar(noticias)
    historias = []
    for g in grupos:
        por = {}
        for i in g["items"]:
            n = noticias[i]
            por.setdefault(n["medio"], n)
        if len(por) >= 3:
            idiomas_g = {info[m]["idioma"] for m in por}
            palabras_clave = [w for w, _ in sorted(g["centro"].items(), key=lambda x: -x[1])[:5]]
            historias.append({
                "medios": len(por),
                "idiomas": len(idiomas_g),
                "fecha": g["fecha"],
                "clave": palabras_clave,
                "titulares": [{"medio": m, "titulo": n["titulo"], "enlace": n["enlace"],
                               "tono": tono(norm(n["titulo"]))[0],
                               **({"original": n["original"]} if "original" in n else {})}
                              for m, n in sorted(por.items(), key=lambda x: (x[1]["idioma"] != "es", x[1]["idioma"], x[0]))],
            })
    # Primero las noticias que cruzan más idiomas: son las que permiten comparar
    historias.sort(key=lambda h: (-min(h["idiomas"], 4), -h["medios"], -h["fecha"]))

    fechas = [n["fecha"] for n in noticias]
    resultado = {
        "total": len(noticias),
        "desde": min(fechas), "hasta": max(fechas),
        "medios": [{"medio": m, **info[m], "titulares": por_medio[m]} for m in medios],
        "paises": list(PAISES),
        "agenda": agenda_out,
        "idiomas": [{"idioma": l, "medios": sum(info[m]["idioma"] == l for m in medios),
                     "titulares": sum(por_medio[m] for m in medios if info[m]["idioma"] == l)} for l in idiomas],
        "agenda_idioma": agenda_idioma,
        "tono_idioma": tono_idioma,
        "tono": tono_out,
        "pares": pares_out,
        "historias": historias[:80],
        "titulares": sorted(indice, key=lambda x: -x["f"]),
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False)
    print(f"{len(noticias)} titulares, {len(medios)} medios, {len(historias)} historias compartidas → {SALIDA}")


if __name__ == "__main__":
    main()
