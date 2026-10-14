# Scaner: radiografía de la web

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
