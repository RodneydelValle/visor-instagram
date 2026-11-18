import sys, site, base64, json, zlib, time, re, random, string
from urllib.parse import urlparse, parse_qs
sys.path.append(site.getusersitepackages())
from playwright.sync_api import sync_playwright

OUT, URL = sys.argv[1], sys.argv[2]
PRESETS = {'visor_instagram_loteria'}
store = {}                       # url -> bytes
porid = {}                       # (cloud, public_id) -> url
cnt = {'upload': 0, 'probe': 0, 'malo': 0, 'img': 0}
cfg = {'cors': True, 'delay': 0, 'retener': False}
retenidas = []
PROMPT = {'texto': None}
def soltar():
    for r, k in retenidas: r.fulfill(**k)
    retenidas.clear()
fallas = []
def ok(cond, msg):
    print(('OK   ' if cond else 'FALLA') + ' ' + msg)
    if not cond: fallas.append(msg)

def multipart(req):
    ct = req.headers.get('content-type', '')
    b = ct.split('boundary=')[-1].encode()
    campos = {}
    for parte in (req.post_data_buffer or b'').split(b'--' + b):
        if b'name="' not in parte: continue
        cab, _, val = parte.partition(b'\r\n\r\n')
        nombre = re.search(rb'name="([^"]+)"', cab).group(1).decode()
        campos[nombre] = val[:-2] if val.endswith(b'\r\n') else val
    return campos

def on_upload(route):
    req = route.request
    cloud = urlparse(req.url).path.split('/')[2]
    f = multipart(req)
    h = {'Access-Control-Allow-Origin': '*'}
    preset = f.get('upload_preset', b'').decode()
    if preset not in PRESETS:
        cnt['malo'] += 1
        return route.fulfill(status=400, headers=h, content_type='application/json', body=json.dumps({"error": {"message": "Upload preset not found"}}))
    if 'return_delete_token' in f:
        return route.fulfill(status=400, headers=h, content_type='application/json', body=json.dumps({"error": {"message": "Return delete token parameter is not allowed when using unsigned upload."}}))
    archivo = f.get('file', b'').decode()
    datos = base64.b64decode(archivo.split(',', 1)[1])
    pid = f.get('public_id', b'').decode() or ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
    if 'public_id' in f: cnt['probe'] += 1
    else: cnt['upload'] += 1
    clave = (cloud, pid)
    if clave in porid:
        k = dict(status=200, headers=h, content_type='application/json', body=json.dumps({"secure_url": porid[clave], "public_id": pid, "existing": True}))
    else:
        url = f'https://res.cloudinary.com/{cloud}/image/upload/v1795012102/{pid}.jpg'
        store[url] = datos; porid[clave] = url
        k = dict(status=200, headers=h, content_type='application/json', body=json.dumps({"secure_url": url, "public_id": pid, "existing": False, "asset_folder": "visor-instagram"}))
    if cfg['retener']: retenidas.append((route, k))
    else: route.fulfill(**k)

def on_img(route):
    cnt['img'] += 1
    u = route.request.url
    h = {'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' if cfg['cors'] else 'https://otro.example'}
    route.fulfill(status=200 if u in store else 404, headers=h, content_type='image/jpeg', body=store.get(u, b''))

def preparar(ctx, dialogs):
    # modo Local para estas pruebas (Grupal se prueba aparte, con Firebase real)
    ctx.add_init_script("try{const u=JSON.parse(localStorage.getItem('visor-ui')||'{}');if(!u.espacio){u.espacio='local';localStorage.setItem('visor-ui',JSON.stringify(u))}}catch(e){}")
    ctx.route('https://www.gstatic.com/firebasejs/**', lambda r: r.abort())
    ctx.route('https://api.cloudinary.com/**', on_upload)
    ctx.route('https://res.cloudinary.com/**', on_img)
    return nueva_pagina(ctx, dialogs)

def nueva_pagina(ctx, dialogs):
    pg = ctx.new_page(); errs = []
    def con(m):
        if m.type == 'error' and not any(x in m.text for x in ('Failed to load resource', 'blocked by CORS', 'Error loading background-image')):
            errs.append(m.text)
    pg.on('console', con)
    pg.on('pageerror', lambda e: errs.append('PAGEERROR: ' + str(e)))
    def dlg(d):
        dialogs.append(d.message)
        if d.type == 'prompt' and PROMPT['texto'] is not None:
            d.accept(PROMPT['texto']); PROMPT['texto'] = None
        else:
            d.accept()
    pg.on('dialog', dlg)
    return pg, errs

def imagenes(pg, n, o=0, nombre='f'):
    datos = pg.evaluate('''([n,o])=>{const cols=['#e63946','#f4a261','#2a9d8f','#264653','#e9c46a','#8338ec','#3a86ff','#ff006e','#06d6a0','#118ab2'];const out=[];
      for(let i=0;i<n;i++){const k=document.createElement('canvas');k.width=600;k.height=750;const x=k.getContext('2d');x.fillStyle=cols[(i+o)%cols.length];x.fillRect(0,0,600,750);
      x.fillStyle='#fff';x.font='bold 200px sans-serif';x.textAlign='center';x.fillText(String(i+o+1),300,450);out.push(k.toDataURL('image/png').split(',')[1])}return out}''', [n, o])
    return [{'name': f'{nombre}{i}.png', 'mimeType': 'image/png', 'buffer': base64.b64decode(d)} for i, d in enumerate(datos)]

def esperar(pg):
    pg.wait_for_function('()=>activos===0&&cola.length===0', timeout=20000); pg.wait_for_timeout(250)

def toast(pg): return pg.locator('#toast').text_content()

def pixel(pg, path, x, y):
    b64 = base64.b64encode(open(path, 'rb').read()).decode()
    return pg.evaluate('''async([b,x,y])=>{const im=new Image();im.src='data:image/png;base64,'+b;await im.decode();const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const g=c.getContext('2d');g.drawImage(im,0,0);return [...g.getImageData(x,y,1,1).data]}''', [b64, x, y])

def compartir(pg):
    pg.click('#bShare'); pg.wait_for_selector('#dlg.on textarea', timeout=15000)
    link = pg.locator('#dlg textarea').input_value()
    pg.locator('#dlg button', has_text='Cerrar').click()
    return link

with sync_playwright() as pw:
    br = pw.chromium.launch()
    # ===================== A: dueña del perfil =====================
    dA = []
    ctxA = br.new_context(viewport={'width': 1400, 'height': 1000}, accept_downloads=True)
    A, errA = preparar(ctxA, dA)
    A.goto(URL); A.wait_for_timeout(800)
    ok(A.evaluate('typeof html2canvas') == 'function', 'html2canvas carga con su huella de seguridad (SRI)')
    A.uncheck('#asNew')
    A.set_input_files('#fPosts', imagenes(A, 2)); A.wait_for_timeout(400); esperar(A)
    ok(A.locator('.tag.st.nube').count() == 2 and cnt['upload'] == 2, 'sin configurar nada, las imágenes se suben solas a la nube del equipo')
    ok(A.evaluate("P.posts.every(p=>p.img.startsWith('https://res.cloudinary.com/xwak6fqd/'))"), 'van a la nube xwak6fqd')
    # otra nube: preset malo y bueno
    A.click('#secNube > summary'); A.click('#secNube details > summary')
    A.fill('#nCloud', 'otra-nube'); A.fill('#nPreset', 'no_existe'); A.click('#bNube'); A.wait_for_timeout(500)
    ok('no existe ese upload preset' in toast(A) and A.evaluate('nubePropia()') is None, 'otra nube con preset inexistente: aviso claro y no se guarda')
    A.fill('#nPreset', 'visor_instagram_loteria'); A.click('#bNube'); A.wait_for_timeout(500)
    ok(A.evaluate('getNube().cloud') == 'otra-nube' and cnt['probe'] >= 1, 'otra nube válida se prueba y se guarda')
    A.click('#bNubeEquipo'); A.wait_for_timeout(200)
    ok(A.evaluate('getNube().cloud') == 'xwak6fqd', '«Volver a la del equipo» funciona')
    # 3 propuestas + avatar + imagen repetida
    A.check('#asNew')
    A.set_input_files('#fPosts', imagenes(A, 3, 2)); A.wait_for_timeout(400); esperar(A)
    ok(A.locator('.tag.st.nube').count() == 5, '3 propuestas suben solas (5 en la nube)')
    A.set_input_files('#fAvatar', imagenes(A, 1, 7)); A.wait_for_timeout(400); esperar(A)
    ok(A.evaluate('P.perfil.avatar').startswith('https://res.cloudinary.com/'), 'foto de perfil subida')
    u0 = cnt['upload']
    rep = imagenes(A, 1, 9, 'rep')
    A.set_input_files('#fPosts', [rep[0], dict(rep[0], name='rep_b.png')]); A.wait_for_timeout(400); esperar(A)
    ok(cnt['upload'] - u0 == 1 and A.evaluate("P.posts[0].img===P.posts[1].img"), 'la misma imagen dos veces se sube una sola vez')
    A.locator('.pitem').nth(0).locator('[data-a=del]').click()   # quitar la repetida (confirm se acepta solo)
    A.wait_for_timeout(200)
    # editar y compartir v1
    A.locator('.pitem').nth(0).locator('[data-a=pin]').click(); A.wait_for_timeout(100)
    A.locator('.pitem').nth(1).locator('[data-a=pin]').click(); A.wait_for_timeout(100)
    A.locator('.pitem').nth(0).locator('textarea').fill('Descripción de prueba 🎉')
    A.locator('.pitem').nth(3).locator('select').select_option('reel')
    A.fill('#pUser', 'kino.equipo'); A.wait_for_timeout(500)
    ok('pend' in (A.get_attribute('#bShare', 'class') or ''), 'con cambios sin compartir, el botón muestra el punto')
    PROMPT['texto'] = 'Kino oficial'
    A.click('#bRenProj'); A.wait_for_timeout(300)
    ok(A.evaluate('P.nombre') == 'Kino oficial', 'renombrar proyecto funciona')
    link1 = compartir(A)
    ok('pend' not in (A.get_attribute('#bShare', 'class') or ''), 'tras compartir, el punto se apaga')
    ok('#p=z' in link1, f'link 1 generado ({len(link1)} caracteres)')
    ok(A.evaluate('cambiosLocales(P)') is False, 'tras compartir no quedan cambios pendientes')
    link1b = compartir(A)
    ok(A.evaluate('P.hist.length') == 1, 'compartir de nuevo sin cambios no crea otra versión')
    with A.expect_download() as d: A.click('#bExport')
    d.value.save_as(OUT + '/v3_export.json')
    A.set_input_files('#fImport', OUT + '/v3_export.json'); A.wait_for_timeout(600)
    ok('Ya tenías esta versión' in toast(A) and not A.locator('#dlg.on').count(), 'importar tu propio archivo no inventa un conflicto')

    # ===================== B: compañera =====================
    dB = []
    ctxB = br.new_context(viewport={'width': 1400, 'height': 1000}, accept_downloads=True)
    B, errB = preparar(ctxB, dB)
    B.goto(link1); B.wait_for_timeout(1200)
    ok('#p=' not in B.url, 'el link se limpia de la barra')
    ok(B.evaluate('P.perfil.usuario') == 'kino.equipo' and B.evaluate('P.posts.length') == 6, 'B ve el perfil y las 6 publicaciones')
    ok(B.evaluate('P.posts.filter(p=>p.fijado).length') == 2 and B.evaluate("P.posts.some(p=>p.tipo==='reel')"), 'B ve fijadas y reel')
    B.locator('.phone .cell[data-id]').first.click(); B.wait_for_timeout(300)
    ok('Descripción de prueba' in B.locator('#postBox .txt').text_content(), 'B ve la descripción')
    B.keyboard.press('Escape')
    r = B.evaluate('''()=>{const f=document.querySelector('#frames').getBoundingClientRect();const c=document.querySelector('.phone .cell[data-id]').getBoundingClientRect();return [Math.round((c.left-f.left+c.width*0.15)*2),Math.round((c.top-f.top+c.height*0.5)*2)]}''')
    with B.expect_download() as d: B.click('#bShot')
    d.value.save_as(OUT + '/v3_descarga.png')
    px = pixel(B, OUT + '/v3_descarga.png', r[0], r[1])
    ok(px[3] == 255 and max(px[:3]) - min(px[:3]) > 40, f'la descarga incluye las imágenes de la nube (pixel {px})')
    cfg['cors'] = False
    with B.expect_download() as d: B.click('#bShot')
    cfg['cors'] = True
    ok('no se pudieron incluir' in toast(B), 'si la nube no deja copiar, avisa en vez de fallar')
    B.goto(link1); B.wait_for_timeout(900)
    ok('Ya tenías esta versión' in toast(B) and B.locator('#selProj option').count() == 1, 'reabrir el mismo link no duplica (y no queda un «Mi perfil» vacío)')
    B.locator('.pitem').nth(0).locator('textarea').fill('Texto de B v2'); B.wait_for_timeout(500)
    link2 = compartir(B)

    # ===================== versiones en A =====================
    A.goto(link2); A.wait_for_timeout(1000)
    ok('versión más nueva' in toast(A) and A.evaluate('P.posts[0].desc') == 'Texto de B v2', 'link más nuevo (sin cambios locales): se actualiza solo')
    A.goto(link1); A.wait_for_selector('#dlg.on', timeout=5000)
    ok('ANTERIOR' in A.locator('#dlg').text_content(), 'link más antiguo: avisa que es anterior')
    A.keyboard.press('Enter'); A.wait_for_timeout(400)
    ok(A.evaluate('P.posts[0].desc') == 'Texto de B v2', 'un Enter apurado se queda con la versión propia (no borra nada)')
    A.locator('.pitem').nth(1).locator('textarea').fill('Cambio local de A'); A.wait_for_timeout(500)
    B.locator('.pitem').nth(2).locator('textarea').fill('Texto de B v3'); B.wait_for_timeout(500)
    link3 = compartir(B)
    A.goto(link3); A.wait_for_selector('#dlg.on', timeout=5000)
    ok('cambios que no has compartido' in A.locator('#dlg').text_content(), 'cambios locales + link nuevo: pregunta')
    A.locator('#dlg button', has_text='Abrir como copia aparte').click(); A.wait_for_timeout(400)
    ok(A.locator('#selProj option', has_text='(copia)').count() == 1, 'abre como copia aparte')
    A.goto(link3); A.wait_for_selector('#dlg.on', timeout=5000)
    A.locator('#dlg button', has_text='Reemplazar mi copia').click(); A.wait_for_timeout(400)
    ok(A.evaluate("P.posts.some(p=>p.desc==='Texto de B v3')"), 'reemplazar deja la versión de B')

    # ===================== carreras con subidas lentas =====================
    cfg['retener'] = True
    A.set_input_files('#fPosts', imagenes(A, 1, 4)); A.wait_for_function("()=>P.posts.some(x=>x.img.startsWith('data:'))", timeout=10000); A.wait_for_timeout(400)
    nuevo = A.evaluate('''()=>{const k=document.createElement('canvas');k.width=40;k.height=40;const x=k.getContext('2d');x.fillStyle='#00ff00';x.fillRect(0,0,40,40);return k.toDataURL('image/jpeg',.9)}''')
    A.evaluate('''(u)=>{const p=P.posts.find(x=>!x.fijado&&x.img.startsWith('data:'));p.img=u;encolarSi(P,p,'img');window.__pid=p.id}''', nuevo)
    A.wait_for_timeout(400); soltar(); A.wait_for_timeout(300); soltar(); esperar(A)
    fin = A.evaluate("P.posts.find(p=>p.id===window.__pid).img")
    ok(fin.startswith('https://res.cloudinary.com/') and len(store.get(fin, b'')) < 3000, 'cambiar la imagen mientras sube deja la nueva')
    # borrar un proyecto mientras sube
    n0 = A.locator('#selProj option').count()
    PROMPT['texto'] = 'Para borrar'
    A.click('#bNewProj'); A.wait_for_timeout(300)
    A.set_input_files('#fPosts', imagenes(A, 2, 5)); A.wait_for_function("()=>P.posts.some(x=>x.img.startsWith('data:'))", timeout=10000); A.wait_for_timeout(400)
    A.click('#bDelProj'); A.wait_for_timeout(200)
    soltar(); A.wait_for_timeout(300); soltar(); esperar(A); A.wait_for_timeout(600)
    ids = A.evaluate("DB.all().then(a=>a.map(p=>p.nombre))")
    print('     (proyectos guardados:', ids, ')')
    ok('Para borrar' not in ids and A.locator('#selProj option').count() == n0, 'borrar un proyecto mientras sube: no reaparece')
    # duplicar mientras sube
    u0 = cnt['upload']
    A.set_input_files('#fPosts', imagenes(A, 1, 6)); A.wait_for_function("()=>P.posts.some(x=>x.img.startsWith('data:'))", timeout=10000); A.wait_for_timeout(400)
    A.click('#bDupProj'); A.wait_for_timeout(300)
    soltar(); A.wait_for_timeout(300); soltar(); esperar(A); cfg['retener'] = False
    ok(cnt['upload'] - u0 == 1 and A.evaluate("P.posts.every(p=>!p.img.startsWith('data:'))"), 'duplicar mientras sube: la copia también queda en la nube, sin subir dos veces')

    # ===================== dos pestañas =====================
    A2, errA2 = nueva_pagina(ctxA, dA)
    A2.goto(URL); A2.wait_for_timeout(900)
    A2.evaluate("(id)=>{const s=document.querySelector('#selProj');s.value=id;s.dispatchEvent(new Event('change'))}", A.evaluate('P.id'))
    A.fill('#pUser', 'desde.pestana.1'); A.wait_for_timeout(1200)
    ok(A2.evaluate('P.perfil.usuario') == 'desde.pestana.1', 'la otra pestaña se entera del cambio')
    A2.close()

    # ===================== links y datos maliciosos =====================
    dC = []
    ctxC = br.new_context(viewport={'width': 1200, 'height': 900})
    C, errC = preparar(ctxC, dC)
    C.goto(URL); C.wait_for_timeout(700)
    good = 'https://res.cloudinary.com/xwak6fqd/image/upload/v1/ok'
    malo = {"v": 3, "sid": "evil1234", "vid": "vvvv1111", "hist": ["vvvv1111", "<script>"], "nombre": "<img src=x onerror=alert(1)>",
            "ui": {"ratio": "1/1;background:red"},
            "perfil": {"usuario": "<script>alert(2)</script>", "avatar": "https://res.cloudinary.com/x/image/upload/a.jpg');background:url('javascript:alert(3)", "bio": "<b>hola</b>"},
            "destacadas": [{"img": "javascript:alert(6)", "titulo": "<u>t</u>"}],
            "posts": [{"id": "\"><svg onload=alert(4)>", "img": "https://res.cloudinary.com/x/image/upload/a.jpg') ; } body{display:none} .x{('", "desc": "x"},
                      {"id": "bueno123", "img": good + "/1.jpg", "desc": "<img src=x onerror=alert(5)>", "fijado": True},
                      {"id": "bueno123", "img": good + "/2.jpg", "fijado": True},
                      {"img": good + "/3.jpg", "fijado": True}, {"img": good + "/4.jpg", "fijado": True},
                      {"img": "data:image/png;base64,iVBORw0KGgo=", "desc": "incrustada escondida"},
                      {"img": "https://i.ibb.co/x/y.jpg", "desc": "otro servicio"}]}
    code = 'j' + base64.urlsafe_b64encode(json.dumps(malo).encode()).decode().rstrip('=')
    C.goto(URL + '#p=' + code); C.wait_for_timeout(1200)
    ok(len(dC) == 0, f'link malicioso: no se ejecuta nada (diálogos {dC})')
    ok(C.evaluate('P.posts.length') == 4, 'link malicioso: se descartan imágenes falsas, incrustadas y de otros servicios')
    ok(C.evaluate('P.posts.filter(p=>p.fijado).length') == 3 and C.evaluate('new Set(P.posts.map(p=>p.id)).size') == 4, 'link malicioso: máx. 3 fijadas e ids corregidos')
    ok(C.evaluate("P.hist.join()") == 'vvvv1111' and C.evaluate("ui.ratio") == '3/4', 'link malicioso: historia y vista inyectadas se limpian')
    ok(C.locator('#selProj option').count() == 1 and C.locator('#selProj option').first.text_content() == '<img src=x onerror=alert(1)>', 'link malicioso: textos se ven literales (y no queda un «Mi perfil» vacío)')
    dV = []
    ctxV = br.new_context(); ctxV.add_init_script('delete window.DecompressionStream')
    V, errV = preparar(ctxV, dV)
    V.goto(link1); V.wait_for_timeout(900)
    ok(any('demasiado antiguo' in m for m in dV), 'navegador antiguo: explica el problema y sugiere el archivo')
    ctxV.close()
    C.goto(URL + '#p=zAAAAbbbb'); C.wait_for_timeout(700)
    ok(any('No se pudo abrir el link' in m for m in dC), 'link dañado: aviso claro')
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    bomba = co.compress(b'{"perfil":{},"posts":[],"x":"' + b'A' * 30_000_000) + co.flush()
    n0 = len(dC)
    C.goto(URL + '#p=z' + base64.urlsafe_b64encode(bomba).decode().rstrip('=')); C.wait_for_timeout(2500)
    ok(any('demasiado grande' in m for m in dC[n0:]), 'link inflado se corta')
    # proyecto dañado guardado por una versión anterior
    C.evaluate('''()=>new Promise(r=>{const t=DB.db.transaction('proy','readwrite');t.objectStore('proy').put({id:'viejo1',nombre:'Guardado viejo',creado:1,sid:'viejo1sid',rev:5,sinc:0,
      perfil:{usuario:'v',avatar:''},destacadas:[],posts:[{id:'"><img src=x onerror=alert(9)>',img:'data:image/jpeg;base64,/9j/AAAA',desc:'x',fijado:true,tipo:'foto'}]});t.oncomplete=r})''')
    C.reload(); C.wait_for_timeout(1200)
    ok(len([m for m in dC if 'alert' in m or m == '9']) == 0 and C.evaluate("proyectos.some(p=>p.nombre==='Guardado viejo'&&RX_ID.test(p.posts[0].id))"), 'lo guardado por versiones anteriores se limpia al abrir')
    # archivo de la versión 1 con imagen incrustada: se importa y se sube solo
    viejo = {"visor": 1, "proyecto": {"id": "abc", "nombre": "Proyecto viejo", "perfil": {"usuario": "viejo", "botones": "Seguir"}, "destacadas": [],
             "posts": [{"id": "p1abc", "img": "data:image/jpeg;base64," + base64.b64encode(next(iter(store.values()))).decode(), "desc": "vieja", "fijado": True}]}}
    C.set_input_files('#fImport', {'name': 'viejo.json', 'mimeType': 'application/json', 'buffer': json.dumps(viejo).encode()})
    C.wait_for_timeout(500); esperar(C)
    ok(C.evaluate('P.nombre') == 'Proyecto viejo' and C.locator('.tag.st.nube').count() == 1, 'archivo antiguo: se importa y su imagen sube sola')
    C.set_viewport_size({'width': 390, 'height': 850}); C.wait_for_timeout(300)
    ok(C.evaluate('document.documentElement.scrollWidth') <= 390, 'sin desborde horizontal en celular')
    A.goto(URL); A.wait_for_timeout(800); A.click('#secNube > summary'); A.wait_for_timeout(200)
    A.screenshot(path=OUT + '/v3_panel.png')
    todos = errA + errB + errC
    ok(not todos, 'sin errores de consola' + ('' if not todos else ': ' + ' | '.join(todos[:4])))
    br.close()
print('\nRESUMEN:', 'TODO OK' if not fallas else f'{len(fallas)} falla(s)')
print('contadores', cnt)
