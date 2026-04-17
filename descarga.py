import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURACIÓN SEGURA ---
ANIO = "2021"
ARCHIVO_CSV = f"tesis_{ANIO}_completo.csv"
HILOS = 10  # Bajamos a 10 para no asustar al servidor
PAUSA_PAGINA = 0.5 # Pausa de medio segundo entre páginas

def extraer_datos_tesis(link, session):
    try:
        res = session.get(link, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        t, a, g = "Sin Título", "Sin Autor", "Sin Grado"
        for r in soup.find_all('tr'):
            th, td = r.find('th'), r.find('td')
            if th and td:
                label = th.get_text(strip=True).lower()
                valor = re.sub(r'\s+', ' ', td.get_text(strip=True))
                if "título" in label or "titulo" in label: t = valor.split('/')[0].strip()
                elif "sustentante" in label and "asesor" not in label: a = re.sub(r'[\,\s\xa0]*sustentante\.', '', valor).strip()
                elif "grado" in label: g = re.sub(r'^[\W_]+', '', valor)
                
        return {"Título": t, "Autor": a, "Año": ANIO, "Grado": g}
    except: 
        return None

def main():
    session = requests.Session()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # --- SISTEMA DE REANUDACIÓN AUTOMÁTICA ---
    jump_actual = 1
    total_guardadas = 0
    
    if os.path.exists(ARCHIVO_CSV):
        try:
            df_existente = pd.read_csv(ARCHIVO_CSV)
            total_guardadas = len(df_existente)
            # Calculamos la página exacta donde se quedó (redondeando hacia abajo)
            jump_actual = max(1, (total_guardadas // 10) * 10 - 10) 
            print(f"🔄 Archivo detectado. Reanudando desde el salto (jump): {jump_actual}...")
        except Exception as e:
            print(f"⚠️ Error leyendo CSV, empezando desde 1. ({e})")
            
    print(f"🚀 INICIANDO CONEXIÓN - AÑO {ANIO}")
    
    # 1. Tramitar el Ticket nuevo
    res_ini = session.get("https://tesiunam.dgb.unam.mx/F?func=find-b-0&local_base=TES01", headers=headers)
    soup_ini = BeautifulSoup(res_ini.text, 'html.parser')
    
    # Manejo de error por si Aleph nos bloqueó temporalmente
    form = soup_ini.find('form', attrs={'name': 'form1'})
    if not form:
        print("❌ Aleph no nos está dando acceso. El servidor puede estar saturado. Espera 2 minutos e intenta de nuevo.")
        return
        
    url_token = form['action']
    
    payload = {
        "func": "find-b", "request": "de", "find_code": "WRD", 
        "filter_code_2": "WYR", "filter_request_2": ANIO, "local_base": "TES01"
    }
    res_busqueda = session.get(url_token, params=payload, headers=headers)
    
    m_set = re.search(r'set_number=(\d+)', res_busqueda.text)
    if not m_set:
        print("❌ Error: No se pudo iniciar la sesión con Aleph.")
        return
    set_number = m_set.group(1)
    print(f"🔑 Ticket activo: {set_number}")

    enlaces_anteriores = []
    strikes = 0

    while True:
        # 2. Navegar a la página
        res_pag = session.get(url_token, params={"func": "short-jump", "jump": str(jump_actual).zfill(6), "set_number": set_number}, headers=headers)
        soup = BeautifulSoup(res_pag.text, 'html.parser')
        filas = soup.find_all('tr')
        
        # Extraer links
        links_actuales = [f.find_all('td')[0].find('a')['href'] for f in filas if len(f.find_all('td')) >= 5 and f.find_all('td')[0].find('a')]
        
        # 3. REGLA DE LOS 3 STRIKES
        if not links_actuales:
            print(f"\n🛑 Catálogo vacío en el salto {jump_actual}. Posible corte de servidor o fin real.")
            break
            
        if links_actuales == enlaces_anteriores:
            strikes += 1
            print(f"   ⚠️ Trampa detectada (Strike {strikes}/3)")
            if strikes >= 3:
                print("\n🛑 Límite de repeticiones. ¡Año completado!")
                break
        else:
            strikes = 0
            enlaces_anteriores = links_actuales
            
            # 4. Procesamiento
            resultados = []
            with ThreadPoolExecutor(max_workers=HILOS) as executor:
                futuros = [executor.submit(extraer_datos_tesis, url, session) for url in links_actuales]
                for futuro in as_completed(futuros):
                    data = futuro.result()
                    if data and data["Título"] != "Sin Título":
                        resultados.append(data)
            
            # 5. Guardado Inmediato
            if resultados:
                df_temp = pd.DataFrame(resultados)
                # Si es la primera escritura y no hay archivo, ponemos header. Si ya hay archivo, no ponemos header.
                df_temp.to_csv(ARCHIVO_CSV, mode='a', header=not os.path.exists(ARCHIVO_CSV), index=False, encoding='utf-8-sig')
                total_guardadas += len(resultados)
                print(f"📦 Salto {jump_actual} procesado | Total guardadas: {total_guardadas}")
        
        jump_actual += 10
        time.sleep(PAUSA_PAGINA) # <--- La clave para no ser baneados

    print("-" * 30)
    print(f"✅ EXTRACCIÓN DETENIDA. Revisa tu archivo CSV.")

if __name__ == "__main__":
    main()
