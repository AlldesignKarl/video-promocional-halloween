# Alldesign Karl · Anuncio de Halloween

Anuncio vertical de **20 s** (1080×1920, 30 fps, H.264 + AAC) para Reels, TikTok, Stories y WhatsApp.
Protagonistas: la **colección de Halloween** de la tienda online [alldesignkarl.com](https://alldesignkarl.com)
el **10 % de descuento del 14 al 24 de octubre** y la invitación a las tiendas: **¿Tienes una tienda?
Colabora con nosotros**.

<img src="video/portada.jpg" width="270" alt="Portada del anuncio">

## Archivos finales

| Archivo | Uso |
|---|---|
| [`video/AlldesignKarl_Halloween_1080x1920.mp4`](video/AlldesignKarl_Halloween_1080x1920.mp4) | Máxima calidad (Instagram, TikTok, Facebook, YouTube Shorts, web) |
| [`video/AlldesignKarl_Halloween_WhatsApp_720p.mp4`](video/AlldesignKarl_Halloween_WhatsApp_720p.mp4) | Versión ligera para enviar por WhatsApp |
| [`video/portada.jpg`](video/portada.jpg) | Portada / miniatura |
| [`audio/banda_sonora.flac`](audio/banda_sonora.flac) | Música sola (original, -14 LUFS) |

## Guion

| Tiempo | Imagen | Rótulos |
|---|---|---|
| 0,0–3,0 s | La **calabaza de resina con flores** a la luz de las velas: la cámara se acerca despacio, las velas y la purpurina parpadean y flotan motas doradas. | *ALLDESIGN KARL · Colección* **Halloween** · *NOVEDAD · Calabaza de resina con flores* |
| 2,7–3,3 s | Barrido rápido de cámara (con desenfoque de movimiento) hasta la calavera. | — |
| 3,0–6,0 s | La **calavera de resina con flores** sobre su base de madera, de día, con el sol de la ventana en la pared. Se van eligiendo los colores de las rosas y las rosas cambian de color con un destello: negro → azul oscuro → morado oscuro → rosa oscuro → burdeos. | *NOVEDAD · Calavera de resina con flores* · *ELIGE EL COLOR DE LAS ROSAS* con las cinco muestras y el nombre del color |
| 6,0–8,4 s | **Se hace de noche** en la misma toma, como un time-lapse: el sol se vuelve naranja y baja, la habitación pasa a la hora azul y entra la luz de la luna por la ventana. | *Y cuando cae la noche…* |
| 8,4–10,5 s | Clic del interruptor: **la base LED se enciende** (con el parpadeo real de un LED), las calaveras brillan desde dentro e iluminan la pared y la mesa. La cámara se acerca a la calavera de frente. | **se ilumina** · *BASE LED · CON O SIN LUZ* |
| 10,3–12,2 s | La cámara atraviesa la luz y aparece el **colgante de resina con calavera** en la puerta: sus lucecitas titilan y la calavera pasa de blanco a negro con un barrido de luz. | *COLGANTE DE RESINA · Calavera · BLANCO · NEGRO* |
| 12,2–12,9 s | Una nube de murciélagos cruza la pantalla y deja paso a un cielo de noche con luna llena. | — |
| 12,6–14,4 s | **El descuento**: el número cuenta hasta 10 y golpea. | *OFERTA DE HALLOWEEN* · **10 %** · *de descuento* · *Del 14 al 24 de octubre* |
| 14,4–16,5 s | **Para tiendas**: se dibuja con trazo dorado una tienda con toldo naranja y el letrero *TU TIENDA*; se encienden las luces del escaparate y aparecen dentro la calabaza, la calavera encendida y el colgante. | *MAYORISTAS* · **¿Tienes una tienda?** · *Colabora con nosotros* · *VENTA AL POR MAYOR PARA TIENDAS* · *Hazte mayorista en alldesignkarl.com* |
| 16,5–20,0 s | Cierre: vuelve el 10 % como insignia y se monta la ficha de contacto con las tres piezas. | *COLECCIÓN HALLOWEEN* · **Alldesign Karl** · *10 % DE DESCUENTO del 14 al 24 de octubre* · **alldesignkarl.com** · **614 65 37 36** (WhatsApp) · **alldesignkarl@gmail.com** · *TIENDA ONLINE para clientes* · *MAYORISTAS venta al por mayor* · *Hecho a mano en Aragón · Compra segura* · *Feliz Halloween* |

No se mencionan tiendas físicas: solo la tienda online (para clientes) y la venta a mayoristas.

Música original sintetizada para el anuncio (re menor, 100 BPM, sin derechos de terceros): caja de música
al empezar, una campanita por cada color de las rosas, un reloj que se acelera mientras cae la noche, el
clic del interruptor y un golpe cálido con coro al encenderse la calavera, aleteo de murciélagos, el golpe
del 10 %, la tienda que se dibuja y enciende sus luces, y el cierre. Mezcla a -14 LUFS con el pico real por debajo de -1,5 dB (estándar de Instagram,
TikTok y YouTube).

## Fotos usadas

Todas salen de la tienda online ([Alldesignakarl](https://github.com/AlldesignKarl/Alldesignakarl), carpeta `assets/productos`):

- `assets/img/calabaza-resina-flores.jpg` — calabaza de resina con flores.
- `assets/img/calavera/{con,sin}-luz-<color>.jpg` — calavera de resina con flores (las fotos buenas, con la
  base de madera), en negro, burdeos, azul oscuro, morado oscuro y rosa oscuro.
- `assets/img/colgante-calavera-{blanco,negro}.jpg` — colgante de resina con calavera (el de la puerta).

Las primeras fotos de la calavera (las del guante negro, `calavera-rosas-*.jpg`) **no se usan**.

## Cómo se ha hecho

- **Material.** `tools/prep.py` recorta la calavera y su base (rembg, modelo `isnet-general-use`),
  prepara la versión "de día" con la luz apagada (calavera de la foto "sin luz" sobre la base de la foto
  "con luz"), iguala la unión de las dos fotos que forman cada imagen de la tienda, alarga la pared y la
  mesa hasta el formato 9:16 y genera la niebla, la luna, el resplandor del LED y la posición de las
  lucecitas del colgante.
- **La noche, de verdad.** La escena de la calavera se pinta con WebGL: un shader reilumina la foto
  real en tiempo lineal (luz de día con la sombra de la ventana, atardecer, hora azul, luz de luna y la
  luz cálida que sale de la calavera y cae sobre la pared y la mesa), así que el paso del día a la noche
  es una sola toma continua.
- **Composición.** `src/promo.html` monta el anuncio (fotos con movimiento de cámara, rótulos, muestras
  de color, partículas, murciélagos dibujados a mano, cielo y cierre) y todo depende solo del tiempo, así
  que cada render sale idéntico. `tools/render_promo.cjs` captura cada fotograma con varias submuestras
  (desenfoque de movimiento; hasta 10 en el barrido) y `tools/build.py` las promedia, añade un grano fino
  y tramado contra el banding y codifica.
- Tipografías de la marca: Pinyon Script y Cormorant Garamond (las de la web) y Montserrat, todas con
  licencia OFL (`assets/fonts`).

## Notas

- **Precios ocultos.** El vídeo no muestra precios, solo el 10 % de descuento y las fechas. Si se quieren
  añadir, se ponen en los rótulos de `src/promo.html`.
- **Colores de las muestras.** Se sacan de las propias fotos de cada color de rosa.

## Regenerarlo

Requisitos: Node 18+ con Playwright (Chromium), Python 3 con numpy, Pillow, scipy y rembg, y ffmpeg.

```bash
python3 tools/prep.py             # material (recortes, placas, texturas)
python3 tools/build.py            # render, música y vídeo final (reutiliza los fotogramas ya hechos)
python3 tools/build.py --fresh     # vuelve a renderizar todos los fotogramas
# fotogramas sueltos para revisar sin renderizar todo:
NODE_PATH=$(npm root -g) node tools/render_promo.cjs --stills 2,4,9,13,18 --out build/stills
```

Para verlo animado en el navegador: sirve la carpeta del repositorio y abre `src/promo.html?play`
(después de `tools/prep.py`, porque usa `build/prep`).
