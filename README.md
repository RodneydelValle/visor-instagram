# Visor de Perfil (maqueta de Instagram)

Herramienta **solo gráfica** para probar cómo se verá un perfil de Instagram antes de publicar: grilla de publicaciones, 3 fijadas, destacadas, biografía y botones.

**Abrir:** https://rodneydelvalle.github.io/visor-instagram/

## Cómo se usa

1. **Perfil:** foto, usuario, nombre, cifras, categoría, biografía, enlace y botones.
2. **Publicaciones:** sube las imágenes actuales de la cuenta (capturas o archivos, de las 12 a 20 últimas) con la casilla *propuesta* **desmarcada**. Después sube las imágenes nuevas con la casilla **marcada**.
3. **📌 Fijar:** hasta 3 publicaciones, que se muestran primero.
4. **Reordenar:** arrastra las miniaturas en el teléfono o usa ▲ ▼. Si sueltas un archivo sobre una celda, la reemplaza.
5. **Vistas:** *Actual*, *Con propuesta* o *Comparar* (dos teléfonos lado a lado); formato de grilla 3:4, 4:5 o 1:1; modo claro u oscuro.
6. **Descargar imagen:** genera un PNG de lo que se ve, para mostrarlo al equipo.

## Compartir con el equipo

- Cada imagen que agregas **se sube sola a la nube del equipo** (Cloudinary). En la lista verás **☁ en la nube** o **💻 solo en este equipo**. No hay que configurar nada.
- Aprieta **Compartir link** y pégalo en el chat del equipo. Quien lo abra verá el perfil tal como estaba, con las imágenes, sin crear cuentas.
- Si alguien cambia algo (orden, fijadas, textos), el botón **Compartir link** muestra un punto naranjo: vuelve a apretarlo y envía el link nuevo.
- El visor sabe qué versión es más nueva:
  - Si abres un link más nuevo y no tenías cambios sin compartir, se actualiza solo.
  - Si el link es más antiguo que tu copia, o si los dos cambiaron por separado, te pregunta qué hacer. La opción marcada nunca borra tu trabajo.
- Para respaldar o enviar un proyecto como archivo, usa **Exportar archivo** e **Importar archivo**.

Ten en cuenta:

- Cualquiera que tenga el link del visor puede subir imágenes a la nube del equipo, y cualquiera que tenga un link compartido puede ver sus imágenes. Compártelo solo dentro de la empresa.
- Los datos de Cloudinary (cloud name `xwak6fqd` y el preset sin firma `visor_instagram_loteria`, que guarda en la carpeta `visor-instagram`) ya vienen en el visor. Para usar otra cuenta: **Nube del equipo → Usar otra nube de Cloudinary**.
- Las imágenes de prueba quedaron con la etiqueta `visor-prueba` en Cloudinary y se pueden borrar desde la Media Library.

## Pruebas

`pruebas/prueba_completa.py` recorre el visor de punta a punta con Playwright (Python) y un Cloudinary simulado: subidas, links, versiones, conflictos, varias pestañas y links maliciosos. Uso:

```
python -I pruebas/prueba_completa.py <carpeta_de_salida> <url_del_visor>
```
