import streamlit as st
import pandas as pd
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Radar Semántico de Tesis UNAM",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILO ACADÉMICO PRO (UI/UX HOMOGÉNEO) ---
st.markdown("""
    <style>
    /* 1. Fuentes tipográficas */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Source+Serif+4:opsz,wght@8..144,400;8..144,600&display=swap');

    html, body, [class*="css"], .stMarkdown, p, span, div {
        font-family: 'Source Serif 4', serif;
        color: #e0e6ed !important; /* Blanco ligeramente grisáceo para no cansar la vista */
        -webkit-font-smoothing: antialiased;
    }

    /* 2. Títulos Institucionales (Oro) */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #D4AF37 !important; 
        font-weight: 700 !important;
        letter-spacing: 0.5px;
    }

    /* 3. Fondos Globales (Azul Marino Profundo) */
    .stApp {
        background-color: #001233; 
    }
    [data-testid="stSidebar"] {
        background-color: #000a1c !important; /* Sidebar un tono más oscuro */
        border-right: 1px solid #1a2a4c;
    }

    /* 4. Corrección del Multiselect (Etiquetas Rojas -> Oro) */
    span[data-baseweb="tag"] {
        background-color: #D4AF37 !important;
        color: #001233 !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        border: none !important;
    }
    span[data-baseweb="tag"] svg {
        fill: #001233 !important; /* Color de la 'x' para cerrar el tag */
    }
    /* Fondo del cuadro del multiselect */
    div[data-baseweb="select"] > div {
        background-color: #001f4d !important;
        border: 1px solid #1a2a4c !important;
        color: white !important;
    }

    /* 5. Área de Texto (Input) */
    .stTextArea textarea {
        background-color: #001a40 !important;
        color: #ffffff !important;
        border: 1px solid #1a2a4c !important;
        border-radius: 8px;
        padding: 15px !important;
    }
    /* El texto de ejemplo (Placeholder) ahora sí se lee */
    .stTextArea textarea::placeholder {
        color: #5c7899 !important; 
        font-style: italic;
    }
    /* Efecto al hacer clic en la caja */
    .stTextArea textarea:focus {
        border-color: #D4AF37 !important;
        box-shadow: 0 0 0 1px #D4AF37 !important;
    }

    /* 6. Botón de Acción */
    .stButton>button {
        background-color: #D4AF37 !important;
        color: #001233 !important;
        border: none !important;
        font-family: 'Source Serif 4', serif;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-radius: 6px;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #f2ce5e !important; /* Oro más brillante al pasar el mouse */
        transform: translateY(-2px);
    }

    /* 7. Tablas y Tarjetas (DataFrames y Expanders) */
    [data-testid="stDataFrame"] div[data-baseweb="table"] {
        background-color: #001a40 !important;
        border-radius: 8px;
    }
    .streamlit-expanderHeader {
        background-color: #001a40 !important;
        border: 1px solid #1a2a4c !important;
        border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIÓN DE LIMPIEZA EN TIEMPO REAL ---
def categorizar_nivel(grado):
    grado = str(grado).lower()
    if 'licenciatura' in grado: return 'Licenciatura'
    if 'maestría' in grado or 'maestria' in grado: return 'Maestría'
    if 'doctorado' in grado: return 'Doctorado'
    if 'especialidad' in grado: return 'Especialidad'
    return 'Otro / Sin Grado'

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    archivo = "tesis_2020_MASTER.csv"
    if os.path.exists(archivo):
        df = pd.read_csv(archivo)
        df['Nivel_Academico'] = df['Grado'].apply(categorizar_nivel)
        return df
    return None

df = cargar_datos()

# --- SIDEBAR (CENTRO de CONTROL) ---
st.sidebar.title("Filtros")
if df is not None:
    niveles = sorted(df['Nivel_Academico'].unique())
    seleccion_nivel = st.sidebar.multiselect("Nivel Académico", niveles, default=niveles)
    
    anios = sorted(df['Año'].unique())
    if len(anios) > 1:
        seleccion_anio = st.sidebar.slider("Rango de Años", min(anios), max(anios), (min(anios), max(anios)))
    else:
        st.sidebar.info(f"📅 Año disponible: {anios[0]}")
        seleccion_anio = (anios[0], anios[0]) 
    
    st.sidebar.divider()
    st.sidebar.metric(label="Total de tesis cargadas", value=f"{len(df):,}")
else:
    st.sidebar.warning("No se encontró el archivo MASTER.csv")

# --- CUERPO PRINCIPAL ---
st.title("Mi Tesis UNAM")
st.subheader("Planteamiento de tu Investigación")

input_text = st.text_area(
    "Pega aquí tu abstract, hipótesis o idea central:",
    placeholder="Ejemplo: Análisis del mercado de valores en China como motor de financiamiento para PYMES...",
    height=150,
    label_visibility="collapsed" # Ocultamos el label repetitivo para un look más limpio
)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    boton_radar = st.button("Escanear Catálogo", use_container_width=True)

# --- ZONA DE RESULTADOS ---
if boton_radar:
    if not input_text:
        st.error("Por favor, ingresa un texto para analizar.")
    else:
        with st.spinner("Calculando vectores de similitud..."):
            st.success("¡Análisis completado! (Simulación de búsqueda)")
            
            mask = (df['Nivel_Academico'].isin(seleccion_nivel)) & (df['Año'].between(seleccion_anio[0], seleccion_anio[1]))
            resultados = df[mask].head(5) 
            
            st.markdown("### 🏆 Top Coincidencias Encontradas")
            
            for i, row in resultados.iterrows():
                with st.expander(f"📌 {row['Título']}"):
                    st.write(f"**Autor:** {row['Autor']}")
                    st.write(f"**Programa exacto:** {row['Grado']}")
                    st.write(f"**Año:** {row['Año']}")

# --- EXPLORADOR DE DATOS ---
st.divider()
st.markdown("### Registro Completo")
if df is not None:
    mask_global = (df['Nivel_Academico'].isin(seleccion_nivel)) & (df['Año'].between(seleccion_anio[0], seleccion_anio[1]))
    st.dataframe(df[mask_global][['Título', 'Autor', 'Nivel_Academico', 'Grado', 'Año']], use_container_width=True, hide_index=True)
