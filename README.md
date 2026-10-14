# Scaner

**→ [Ver la comparación de titulares (se actualiza cada 3 horas)](https://cmitjans.github.io/Scaner/noticias/)**

Dos experimentos: una radiografía de la web pública y un comparador de cómo cuentan las noticias 63 medios en seis idiomas (carpeta `noticias/`).

## Radiografía de la web

Toma una muestra aleatoria de páginas de la web pública y la resume: idiomas, países, tipos de sitio y rastreadores.

## De dónde salen las páginas

De [Common Crawl](https://commoncrawl.org), una organización sin fines de lucro que rastrea la web pública cada mes y publica el resultado gratis. Este proyecto **no rastrea sitios por su cuenta**: solo lee archivos que Common Crawl ya publicó, saltando a puntos al azar dentro de ellos para obtener una muestra variada.

## Qué se guarda

Para cada página: dominio, idioma, tipo de sitio (tienda, blog, foro, noticias…), rastreadores que carga (Google Analytics, Meta Pixel, etc.), título y un fragmento.

- Las páginas detectadas como **contenido para adultos o apuestas** solo se cuentan: no se guarda su dirección ni su texto.
- La galería de páginas solo incluye páginas en español, inglés, portugués, francés, alemán e italiano, para poder filtrar con más confianza.
- El filtro es automático y puede equivocarse en ambos sentidos.

## Cómo generar una muestra nueva

Pestaña **Actions → Radiografía de la web → Run workflow**. El resultado queda en `datos/datos.json`.

---

# Noticias: misma noticia, distintos titulares

En `noticias/` hay un segundo experimento: recolecta titulares de 16 medios en español (Chile, España, Argentina, EE. UU., Reino Unido, Alemania, Francia, Rusia, China y Venezuela) cada 3 horas y compara cómo cubren los hechos.

- **Fuente:** los RSS de cada medio, o el RSS de Google News filtrado por sitio cuando el medio no tiene uno propio (solo titulares). Solo se guarda título, un resumen corto, fecha y enlace.
- **Qué mide** (`noticias/analizar.py`, con listas de palabras definidas de antemano): qué países aparecen más en cada medio, el tono de los titulares sobre cada país, la elección de palabras con carga ("régimen" o "gobierno", "ataque" u "operación") y titulares de distintos medios sobre el mismo hecho.
- **Limitaciones:** se basa solo en palabras de los titulares, no en leer los artículos; los medios leídos por Google News aportan menos texto; la Voz de América casi no aparece en Google News.

Para actualizar a mano: **Actions → Comparar titulares → Run workflow**.
