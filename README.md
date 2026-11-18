# Visor de Perfil (maqueta de Instagram)

Herramienta **solo gráfica** para probar cómo se verá un perfil de Instagram antes de publicar: grilla de publicaciones, 3 fijadas, destacadas, biografía y botones.

**Abrir:** https://rodneydelvalle.github.io/visor-instagram/

## Local y Grupal

Arriba hay dos botones grandes:

- **💻 Local:** perfiles que solo están en tu navegador. Sirven para probar ideas sin que nadie las vea. Para mostrarlos, usa **Compartir link**: el link lleva una foto del perfil tal como estaba.
- **👥 Grupal:** perfiles del equipo, **en vivo**. Todo lo que cualquiera sube o cambia aparece solo en el visor de los demás, sin mandar links. El link de un perfil grupal siempre abre la versión al día.

Para pasar de uno a otro:

- **📤 Copiar al equipo** (desde Local) crea una copia en Grupal.
- **📥 Copiar a local** (desde Grupal) crea una copia privada.

Así cada persona puede tener su versión de prueba y la versión del equipo.

## Cómo se usa

1. **Perfil:** foto, usuario, nombre, cifras, categoría, biografía, enlace y botones.
2. **Publicaciones:** sube las imágenes actuales de la cuenta (capturas o archivos, de las 12 a 20 últimas) con la casilla *propuesta* **desmarcada**. Después sube las imágenes nuevas con la casilla **marcada**.
3. **📌 Fijar:** hasta 3 publicaciones, que se muestran primero.
4. **Reordenar:** arrastra las miniaturas en el teléfono o usa ▲ ▼. Si sueltas un archivo sobre una celda, la reemplaza.
5. **Vistas:** *Actual*, *Con propuesta* o *Comparar* (dos teléfonos lado a lado); formato de grilla 3:4, 4:5 o 1:1; modo claro u oscuro.
6. **Descargar imagen:** genera un PNG de lo que se ve.

Las imágenes se suben solas a la nube del equipo (Cloudinary). En la lista verás **☁ en la nube** o **💻 solo en este equipo**.

## Para tener en cuenta

- **El acceso es abierto.** Cualquiera que tenga el link del visor puede ver y editar los perfiles grupales y subir imágenes. Compártelo solo dentro de la empresa.
- **Grupal usa Firebase** del proyecto `eventosimp-ec898` (el mismo de IMP TRAVEL), en la colección `visor_equipo`. Las reglas de acceso están en el repositorio de IMP TRAVEL (`firestore.rules`) y se publican a mano en la consola de Firebase.
- **Las imágenes van a Cloudinary**, con cloud name `xwak6fqd` y el preset sin firma `visor_instagram_loteria`, que guarda en la carpeta `visor-instagram`. Para usar otra cuenta: **Nube del equipo → Usar otra nube de Cloudinary**.
- **Archivo:** **Exportar archivo** e **Importar archivo** sirven para respaldar un perfil o pasarlo sin internet. Lo importado queda en Local.

## Pruebas

En `pruebas/` hay pruebas automáticas con Playwright (Python):

- `prueba_completa.py`: modo Local, con Cloudinary simulado. Cubre subidas, links, versiones, conflictos, varias pestañas y links maliciosos.
- `prueba_grupal.py`: modo Grupal con Firebase **real**, en la colección `visor_pruebas`, que se vacía al final.

```
python -I pruebas/prueba_completa.py <carpeta_de_salida> <url_del_visor>
python -I pruebas/prueba_grupal.py <carpeta_de_salida> <url_del_visor>
```
