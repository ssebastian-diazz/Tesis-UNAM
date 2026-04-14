import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from sentence_transformers import SentenceTransformer, util

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Radar de Tesis", layout="wide")
st.title("Radar Semántico de Tesis")
st.markdown("Plataforma de filtrado y ranking de estado del arte usando IA local.")

# --- CARGA DEL MODELO IA (Caché para no recargarlo) ---
@st.cache_resource
def load_model():
    return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

modelo = load_model()

# --- INTERFAZ DE USUARIO ---
with st.sidebar:
    st.header("Configuración de tu Tesis")
    user_keywords = st.text_input("Palabras clave a buscar en el catálogo", value="china mexico")
    
    user_title = st.text_input("Título propuesto de tu tesis", value="Estudio del desarrollo del mercado bursátil en China")
    user_desc = st.text_area("Breve descripción", value="Análisis del sistema bancario y el mercado de valores, abordado desde su proceso histórico de apertura y transformación económica.")
    
    btn_buscar = st.button("Buscar y Analizar", type="primary")

# --- LÓGICA DE EXTRACCIÓN CON PAGINACIÓN ---
def extraer_datos_unam(keywords, max_resultados=75):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # PASO 1: Token de Sesión
        url_inicial = "https://tesiunam.dgb.unam.mx/F?func=find-b-0&local_base=TES01"
        resp_inicial = session.get(url_inicial, headers=headers)
        resp_inicial.encoding = 'utf-8' 
        soup_inicial = BeautifulSoup(resp_inicial.text, 'html.parser')
        
        form_busqueda = soup_inicial.find('form', attrs={'name': 'form1'})
        if not form_busqueda or 'action' not in form_busqueda.attrs:
            st.error("Bloqueo del servidor: No se pudo obtener el token de sesión.")
            return []
            
        url_con_token = form_busqueda['action']
        
        # PASO 2: Búsqueda Inicial (Página 1)
        payload = {
            "func": "find-b",
            "local_base": "TES01",
            "request": keywords,
            "find_code": "WRD",
            "adjacent": "N",
            "filter_code_2": "WYR",
            "filter_request_2": "",
            "filter_code_3": "WYR",
            "filter_request_3": ""
        }
        
        resp = session.get(url_con_token, params=payload, headers=headers)
        resp.encoding = 'utf-8' 
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        resultados = []
        current_jump = 1 # Empezamos en el registro 1
        
        # Bucle de Paginación
        while len(resultados) < max_resultados:
            filas = soup.find_all('tr')
            tesis_en_esta_pagina = 0
            
            for fila in filas:
                if len(resultados) >= max_resultados:
                    break
                    
                columnas = fila.find_all('td')
                if len(columnas) >= 5:
                    script_tag = columnas[3].find('script')
                    titulo = "Sin título"
                    if script_tag and script_tag.string:
                        match_titulo = re.search(r"title\s*=\s*'([^']+)'", script_tag.string)
                        if match_titulo:
                            titulo = match_titulo.group(1).replace('&nbsp;', ' ').strip()
                    
                    enlace_tag = columnas[0].find('a')
                    if enlace_tag and 'href' in enlace_tag.attrs:
                        link_completo = enlace_tag['href']
                        
                        # Extraer detalle individual
                        time.sleep(1) 
                        resp_indiv = session.get(link_completo, headers=headers)
                        resp_indiv.encoding = 'utf-8' 
                        soup_indiv = BeautifulSoup(resp_indiv.text, 'html.parser')
                        
                        facultad = "Facultad no especificada"
                        grado = "Grado no especificado"
                        
                        filas_indiv = soup_indiv.find_all('tr')
                        for f in filas_indiv:
                            th = f.find('th')
                            td = f.find('td')
                            if th and td:
                                texto_th = th.text.strip()
                                texto_td = td.text.strip()
                                if "Grado" in texto_th:
                                    grado = re.sub(r'^[\W_]+', '', texto_td) 
                                if "Nota de tesis" in texto_th:
                                    match_facultad = re.search(r"(Facultad de [^\,]+|Escuela [^\,]+|Instituto [^\,]+)", texto_td)
                                    if match_facultad:
                                        facultad = match_facultad.group(1).strip()

                        resultados.append({
                            "Título": titulo,
                            "Grado": grado,
                            "Facultad": facultad,
                            "Año": columnas[4].text.strip()
                        })
                        tesis_en_esta_pagina += 1
            
            # Si la página actual no tuvo tesis válidas, significa que ya no hay más resultados totales
            if tesis_en_esta_pagina == 0:
                break
                
            # PASO 3: Saltar a la siguiente página si aún faltan resultados
            if len(resultados) < max_resultados:
                current_jump += 10 # Las páginas avanzan de 10 en 10
                payload_pag = {
                    "func": "short-jump",
                    "jump": str(current_jump).zfill(6) # Formato Aleph: "000011", "000021"...
                }
                resp = session.get(url_con_token, params=payload_pag, headers=headers)
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                
        return resultados
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return []

# --- EJECUCIÓN DEL FLUJO ---
if btn_buscar:
    with st.spinner("Navegando y extrayendo resultados... (Esto tomará poco más de 1 minuto por las pausas de seguridad)"):
        tesis_encontradas = extraer_datos_unam(user_keywords, max_resultados=75)
    
    if not tesis_encontradas:
        st.warning("No se encontraron resultados. Intenta con otras palabras.")
    else:
        with st.spinner("Procesando Similitud Semántica y filtrando resultados..."):
            texto_usuario = user_title + ". " + user_desc
            vector_usuario = modelo.encode(texto_usuario)
            
            for tesis in tesis_encontradas:
                vector_tesis = modelo.encode(tesis["Título"])
                similitud = util.cos_sim(vector_usuario, vector_tesis).item()
                tesis["Similitud"] = round(similitud * 100, 2)
                
                if tesis["Similitud"] >= 96:
                    tesis["Zona"] = "🔴 Alerta (Duplicado)"
                elif tesis["Similitud"] >= 81:
                    tesis["Zona"] = "🟢 Estado del Arte (API)"
                elif tesis["Similitud"] >= 50:
                    tesis["Zona"] = "🟡 Contexto General"
                else:
                    tesis["Zona"] = "⚪ Descartable"

        df_completo = pd.DataFrame(tesis_encontradas)
        df_completo = df_completo.sort_values(by="Similitud", ascending=False).reset_index(drop=True)
        
        df_filtrado = df_completo[df_completo["Zona"] != "⚪ Descartable"].reset_index(drop=True)
        tesis_descartadas_count = len(df_completo) - len(df_filtrado)
        
        st.success(f"Búsqueda finalizada. Se evaluaron {len(df_completo)} tesis y la IA descartó **{tesis_descartadas_count}** por falta de relevancia temática.")
        
        st.subheader("Resultados del Filtrado Inteligente")
        
        if df_filtrado.empty:
            st.info("Todas las tesis extraídas fueron clasificadas como 'Descartables' según tu título y descripción. Prueba ajustando tu texto.")
        else:
            st.dataframe(
                df_filtrado[["Similitud", "Zona", "Título", "Grado", "Facultad", "Año"]],
                use_container_width=True,
                height=400
            )
            
            st.markdown("---")
            st.subheader("Siguiente paso: Generación Aumentada (RAG)")
            tesis_api = df_filtrado[df_filtrado["Zona"] == "🟢 Estado del Arte (API)"]
            
            if not tesis_api.empty:
                st.info(f"En un entorno de producción, solo estas **{len(tesis_api)} tesis** serían enviadas a la API de LLM para generar la justificación teórica.")
                for i, row in tesis_api.iterrows():
                    st.write(f"- **{row['Título']}** ({row['Facultad']})")
            else:
                st.write("Ninguna de las tesis extraídas cayó en el umbral del Estado del Arte (81% - 95%). No se gastarán créditos de API.")
