import sys, site
sys.path.append(site.getusersitepackages())
from playwright.sync_api import sync_playwright
URL = sys.argv[1] + '?coleccion=visor_pruebas'
def esp(pg, c, t=20000):
    try: pg.wait_for_function(c, timeout=t); return True
    except Exception: return False
with sync_playwright() as pw:
    br = pw.chromium.launch()
    A = br.new_context().new_page(); B = br.new_context().new_page()
    for pg in (A, B): pg.on('dialog', lambda d: d.accept('PRUEBA verificada') if d.type == 'prompt' else d.accept())
    A.goto(URL); esp(A, "()=>eq.estado==='vivo'")
    A.evaluate('''async()=>{const {F,fs}=eq;const s=await F.getDocs(F.collection(fs,COL));for(const d of s.docs){const p=await F.getDocs(F.collection(fs,COL,d.id,'posts'));await Promise.all(p.docs.map(x=>F.deleteDoc(x.ref)));await F.deleteDoc(d.ref)}}''')
    A.wait_for_timeout(1200); A.click('#veloCrear'); esp(A, "()=>P&&P.equipo")
    B.goto(URL); print('B en el perfil del equipo:', esp(B, "()=>P&&P.equipo&&P.nombre==='PRUEBA verificada'"))
    print('verif inicial A/B:', A.evaluate('P.perfil.verif'), B.evaluate('P.perfil.verif'))
    A.check('#pVerif'); A.wait_for_timeout(300)
    print('B recibe «verificada»:', esp(B, "()=>P.perfil.verif===true", 15000), '| casilla de B:', B.is_checked('#pVerif'), '| insignia en el teléfono de B:', B.locator('.phone .verif').count() > 0)
    B.uncheck('#pRing'); B.check('#pBtnBlue') if not B.is_checked('#pBtnBlue') else B.uncheck('#pBtnBlue')
    print('A recibe aro/azul:', esp(A, "()=>P.perfil.aro===false", 15000))
    C = br.new_context().new_page(); C.goto(URL)
    print('quien abre después ve la insignia:', esp(C, "()=>P&&P.equipo&&P.perfil.verif===true&&document.querySelector('.phone .verif')!==null", 25000))
    A.evaluate('''async()=>{const {F,fs}=eq;const s=await F.getDocs(F.collection(fs,COL));for(const d of s.docs){const p=await F.getDocs(F.collection(fs,COL,d.id,'posts'));await Promise.all(p.docs.map(x=>F.deleteDoc(x.ref)));await F.deleteDoc(d.ref)}}''')
    br.close()
