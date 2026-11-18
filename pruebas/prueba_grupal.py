"""Prueba de Grupal con Firebase REAL, en la colección visor_pruebas (se borra al final).
Cloudinary va simulado: las imágenes reciben direcciones válidas de res.cloudinary.com sin subir nada."""
import sys, site, base64, json, random, string, re, time
from urllib.parse import urlparse
sys.path.append(site.getusersitepackages())
from playwright.sync_api import sync_playwright

OUT, BASE = sys.argv[1], sys.argv[2]
URL = BASE + ('&' if '?' in BASE else '?') + 'coleccion=visor_pruebas'
store = {}
fallas = []
def ok(c, m):
    print(('OK   ' if c else 'FALLA') + ' ' + m, flush=True)
    if not c: fallas.append(m)

def multipart(req):
    b = req.headers.get('content-type', '').split('boundary=')[-1].encode(); campos = {}
    for parte in (req.post_data_buffer or b'').split(b'--' + b):
        if b'name="' not in parte: continue
        cab, _, val = parte.partition(b'\r\n\r\n')
        campos[re.search(rb'name="([^"]+)"', cab).group(1).decode()] = val[:-2] if val.endswith(b'\r\n') else val
    return campos
def on_upload(route):
    f = multipart(route.request); cloud = urlparse(route.request.url).path.split('/')[2]
    pid = f.get('public_id', b'').decode() or ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))
    url = f'https://res.cloudinary.com/{cloud}/image/upload/v1795012102/{pid}.jpg'
    store[url] = base64.b64decode(f['file'].decode().split(',', 1)[1])
    route.fulfill(status=200, headers={'Access-Control-Allow-Origin': '*'}, content_type='application/json', body=json.dumps({"secure_url": url, "public_id": pid}))
def on_img(route):
    u = route.request.url
    route.fulfill(status=200 if u in store else 404, headers={'Access-Control-Allow-Origin': '*'}, content_type='image/jpeg', body=store.get(u, b''))

PROMPT = {'t': None}
def persona(br, nombre):
    ctx = br.new_context(viewport={'width': 1300, 'height': 900})
    ctx.route('https://api.cloudinary.com/**', on_upload); ctx.route('https://res.cloudinary.com/**', on_img)
    pg = ctx.new_page(); errs = []; dl = []
    pg.on('pageerror', lambda e: errs.append(nombre + ': ' + str(e)))
    def dlg(d):
        dl.append(d.message)
        if d.type == 'prompt' and PROMPT['t'] is not None: d.accept(PROMPT['t']); PROMPT['t'] = None
        else: d.accept()
    pg.on('dialog', dlg)
    return ctx, pg, errs, dl

def img(pg, n, o=0):
    datos = pg.evaluate('''([n,o])=>{const c=['#e63946','#2a9d8f','#3a86ff','#ff006e','#8ac926','#ffbe0b'];return Array.from({length:n},(_,i)=>{const k=document.createElement('canvas');k.width=300;k.height=375;const x=k.getContext('2d');x.fillStyle=c[(i+o)%c.length];x.fillRect(0,0,300,375);x.fillStyle='#fff';x.font='bold 120px sans-serif';x.fillText(String(i+o+1),100,230);return k.toDataURL('image/png').split(',')[1]})}''', [n, o])
    return [{'name': f'i{o+i}.png', 'mimeType': 'image/png', 'buffer': base64.b64decode(d)} for i, d in enumerate(datos)]

def esperar(pg, cond, t=20000):
    try: pg.wait_for_function(cond, timeout=t); return True
    except Exception: return False

with sync_playwright() as pw:
    br = pw.chromium.launch()
    ctxA, A, eA, dA = persona(br, 'A'); ctxB, B, eB, dB = persona(br, 'B')
    A.goto(URL)
    ok(esperar(A, "()=>eq.estado==='vivo'", 25000), 'A se conecta al equipo (Firebase real)')
    # limpieza previa por si quedó algo de una prueba anterior
    A.evaluate('''async()=>{const {F,fs}=eq;const s=await F.getDocs(F.collection(fs,COL));for(const d of s.docs){const p=await F.getDocs(F.collection(fs,COL,d.id,'posts'));await Promise.all(p.docs.map(x=>F.deleteDoc(x.ref)));await F.deleteDoc(d.ref)}}''')
    A.wait_for_timeout(1500)
    ok(A.locator('#velo:not(.hidden)').count() == 1 and 'Todavía no hay perfiles' in A.locator('#veloTit').text_content(), 'sin perfiles del equipo: invita a crear el primero')
    PROMPT['t'] = 'PRUEBA vivo'
    A.click('#veloCrear')
    ok(esperar(A, "()=>P&&P.equipo&&P.nombre==='PRUEBA vivo'"), 'A crea un perfil del equipo')
    A.set_input_files('#fPosts', img(A, 2))
    ok(esperar(A, "()=>P.posts.length===2&&P.posts.every(p=>p.img.startsWith('https://'))&&eq.guardando===0"), 'A sube 2 imágenes y se guardan en el equipo')

    B.goto(URL)
    ok(esperar(B, "()=>eq.estado==='vivo'&&P&&P.equipo&&P.nombre==='PRUEBA vivo'", 25000), 'B abre el visor y cae en el perfil del equipo')
    ok(esperar(B, "()=>P.posts.length===2"), 'B ve las 2 imágenes que subió A')
    A.set_input_files('#fPosts', img(A, 1, 2))
    ok(esperar(B, "()=>P.posts.length===3", 15000), 'A sube otra y B la ve aparecer sola')
    # B cambia la descripción de la primera (sin foco después) y A la ve
    pid0 = B.evaluate('P.posts[0].id')
    B.locator(f'.pitem[data-id="{pid0}"] textarea').fill('Escrito por B'); B.locator('#pUser').click()
    ok(esperar(A, f"()=>P.posts.find(p=>p.id==='{pid0}').desc==='Escrito por B'", 15000), 'B escribe una descripción y A la ve')
    # cambios simultáneos en publicaciones distintas: no se pisan
    pid1 = A.evaluate('P.posts[1].id')
    A.evaluate(f"()=>{{const p=P.posts.find(x=>x.id==='{pid1}');p.desc='A al mismo tiempo';guardar()}}")
    B.evaluate(f"()=>{{const p=P.posts.find(x=>x.id==='{pid0}');p.fijado=true;guardar()}}")
    ok(esperar(A, f"()=>P.posts.find(p=>p.id==='{pid0}').fijado===true", 15000) and esperar(B, f"()=>P.posts.find(p=>p.id==='{pid1}').desc==='A al mismo tiempo'", 15000),
       'cambios al mismo tiempo en publicaciones distintas: se guardan los dos')
    # perfil
    A.fill('#pUser', 'kino.envivo'); A.locator('#pName').click()
    ok(esperar(B, "()=>P.perfil.usuario==='kino.envivo'", 15000), 'A cambia el usuario y B lo ve')
    # mientras B escribe, lo que llega no le mueve el texto
    B.locator('#pBio').focus(); B.keyboard.press('Control+End'); B.keyboard.type(' B escribiendo')
    A.fill('#pName', 'Nombre desde A'); A.locator('#pUser').click()
    esperar(B, "()=>P.perfil.nombre==='Nombre desde A'", 15000); B.wait_for_timeout(400)
    B.keyboard.type(' y sigue')
    ok(B.input_value('#pBio').endswith('B escribiendo y sigue') and B.evaluate("document.activeElement.id") == 'pBio', 'mientras B escribe, lo que llega del equipo no le borra el texto ni el cursor')
    ok(B.input_value('#pName') == 'Nombre desde A', 'mientras B escribe la biografía, el campo Nombre ya muestra el cambio de A')
    B.locator('#lblProy').click()
    ok(esperar(A, "()=>P.perfil.bio.endsWith('B escribiendo y sigue')", 15000), 'y A recibe la biografía de B')
    # orden
    A.evaluate("()=>{const ps=ordenados('propuesta');moverPost(ps[ps.length-1].id,ps[0].id);guardar();render()}")
    orden_a = A.evaluate("()=>ordenados('propuesta').map(p=>p.id).join()")
    ok(esperar(B, f"()=>ordenados('propuesta').map(p=>p.id).join()==='{orden_a}'", 15000), 'A reordena y B ve el mismo orden')
    # borrar una publicación
    pid2 = B.evaluate('P.posts[2].id')
    B.locator(f'.pitem[data-id="{pid2}"] [data-a=del]').click()
    ok(esperar(A, f"()=>!P.posts.some(p=>p.id==='{pid2}')", 15000), 'B quita una publicación y desaparece para A')
    # copiar a local y volver
    B.click('#bMover')
    ok(esperar(B, "()=>ui.espacio==='local'&&!P.equipo&&P.posts.length===2"), 'B copia el perfil del equipo a Local')
    B.click('#espGrupal')
    ok(esperar(B, "()=>ui.espacio==='grupal'&&P.equipo&&P.nombre==='PRUEBA vivo'"), 'B vuelve a Grupal y sigue en el mismo perfil')
    # copiar de local al equipo
    A.click('#espLocal'); A.wait_for_timeout(400)
    A.set_input_files('#fPosts', img(A, 1, 4)); esperar(A, "()=>activos===0&&cola.length===0")
    PROMPT['t'] = 'PRUEBA desde local'; A.click('#bRenProj'); A.wait_for_timeout(300)
    A.click('#bMover')
    ok(esperar(A, "()=>ui.espacio==='grupal'&&P.equipo&&P.nombre==='PRUEBA desde local'"), 'A copia un perfil local al equipo')
    ok(esperar(B, "()=>proyectos.some(p=>p.equipo&&p.nombre==='PRUEBA desde local')", 15000), 'B ve aparecer el perfil nuevo en su lista')
    # link del equipo
    A.click('#bShare'); A.wait_for_selector('#dlg.on textarea')
    link = A.locator('#dlg textarea').input_value(); A.locator('#dlg button', has_text='Cerrar').click()
    ok('#equipo=' in link and len(link) < 200, f'link del equipo corto ({len(link)} caracteres)')
    ctxC, C, eC, dC = persona(br, 'C')
    C.goto(link)
    ok(esperar(C, "()=>eq.estado==='vivo'&&P&&P.equipo&&P.nombre==='PRUEBA desde local'&&P.posts.length===1", 25000), 'C abre el link y cae en ese perfil, en vivo')
    # reglas: datos inválidos se rechazan
    r = A.evaluate('''async()=>{const {F,fs}=eq;const res={};
      try{await F.setDoc(F.doc(fs,COL,P.sid,'posts','malo1234'),{img:'javascript:alert(1)',desc:'x',tipo:'foto',propuesta:false,fijado:false,o:1,creado:1});res.img='aceptado'}catch(e){res.img=e.code}
      try{await F.setDoc(F.doc(fs,COL,P.sid,'posts','malo5678'),{img:'https://res.cloudinary.com/x/image/upload/a.jpg',desc:'x'.repeat(3000),tipo:'foto',propuesta:false,fijado:false,o:1,creado:1});res.largo='aceptado'}catch(e){res.largo=e.code}
      try{await F.setDoc(F.doc(fs,'otra_coleccion','abcd1234'),{a:1});res.otra='aceptado'}catch(e){res.otra=e.code}
      try{await F.getDocs(F.collection(fs,'favoritos'));res.fav='aceptado'}catch(e){res.fav=e.code}
      return res}''')
    ok(all(v == 'permission-denied' for v in r.values()), f'las reglas rechazan datos inválidos y colecciones ajenas ({r})')
    # borrar un perfil del equipo: los demás se enteran
    A.once('dialog', lambda d: d.accept())
    C.click('#bDelProj')
    ok(esperar(A, "()=>!proyectos.some(p=>p.equipo&&p.nombre==='PRUEBA desde local')", 15000), 'C borra el perfil y desaparece para A')
    ok(any('borró este perfil' in t for t in [A.locator('#toast').text_content() or '']) or A.evaluate("P.nombre")=='PRUEBA vivo', 'A queda en otro perfil del equipo')
    A.screenshot(path=OUT + '/grupal_A.png'); B.screenshot(path=OUT + '/grupal_B.png')
    # limpieza final
    A.evaluate('''async()=>{const {F,fs}=eq;const s=await F.getDocs(F.collection(fs,COL));for(const d of s.docs){const p=await F.getDocs(F.collection(fs,COL,d.id,'posts'));await Promise.all(p.docs.map(x=>F.deleteDoc(x.ref)));await F.deleteDoc(d.ref)}}''')
    ok(A.evaluate("async()=>(await eq.F.getDocs(eq.F.collection(eq.fs,COL))).size") == 0, 'limpieza: la colección de pruebas queda vacía')
    todos = eA + eB + eC
    ok(not todos, 'sin errores de página' + ('' if not todos else ': ' + ' | '.join(todos[:3])))
    br.close()
print('RESUMEN:', 'TODO OK' if not fallas else f'{len(fallas)} falla(s)')
