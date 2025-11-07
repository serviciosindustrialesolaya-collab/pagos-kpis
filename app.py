# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe, get_as_dataframe

st.set_page_config(page_title="KPIs de Pagos", layout="wide")
st.title("KPIs de Pagos — Demo conectada a Google Sheets")

# ---- Credenciales desde Secrets ----
try:
    sa_info = dict(st.secrets["gcp_service_account"])
    SPREADSHEET_ID = st.secrets["SPREADSHEET_ID"]
except Exception as e:
    st.error("Falta configurar Secrets. Ve a Settings → Secrets y define:\n"
             "[gcp_service_account] … y SPREADSHEET_ID = \"ID_DE_TU_SHEET\"")
    st.stop()

# ---- Autenticación Google ----
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc = gspread.authorize(creds)

# ---- Abrir Sheet y worksheet 'Pagos' ----
headers = [
    "Fecha Registro","Área","Tipo de Pago","Proveedor","ID Registro","Moneda",
    "Monto","Tipo Cambio","Monto en S/","Fecha Vencimiento","Prioridad",
    "Estado","Observaciones","Pagos hoy","Proximos 7 dias"
]
sh = gc.open_by_key(SPREADSHEET_ID)

try:
    ws = sh.worksheet("Pagos")
except gspread.WorksheetNotFound:
    ws = sh.add_worksheet(title="Pagos", rows=2000, cols=len(headers))
    ws.update("A1:Z1", [headers])

# ---- Cargar datos a DataFrame ----
df = get_as_dataframe(ws, evaluate_formulas=True, header=0, dtype=str)
df = df.iloc[0: ]  # quita filas None
if df.empty:
    df = pd.DataFrame(columns=headers)
else:
    df = df[headers] if all(c in df.columns for c in headers) else df

# Normalizaciones suaves (sin romper celdas vacías)
for col in ["Monto","Tipo Cambio","Monto en S/"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col].str.replace(",","", regex=False), errors="coerce")

for col in ["Fecha Registro","Fecha Vencimiento"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

# ---- UI: Filtros simples ----
with st.sidebar:
    st.subheader("Filtros")
    prioridad = st.selectbox("Prioridad", ["(Todas)","Alta","Media","Baja"])
    estado = st.selectbox("Estado", ["(Todas)","Pendiente","Pagado"])

fdf = df.copy()
if "Prioridad" in fdf.columns and prioridad != "(Todas)":
    fdf = fdf[fdf["Prioridad"] == prioridad]
if "Estado" in fdf.columns and estado != "(Todas)":
    fdf = fdf[fdf["Estado"] == estado]

# ---- Editor ----
st.subheader("Base: Pagos (edita y guarda)")
edited = st.data_editor(
    fdf, use_container_width=True, num_rows="dynamic", key="editor"
)

colA, colB = st.columns(2)
with colA:
    if st.button("Refrescar desde Google Sheets"):
        st.rerun()
with colB:
    if st.button("Guardar cambios en Google Sheets", type="primary"):
        # Escribimos TODO el DataFrame filtrado? No: escribimos la base completa.
        # Tomamos 'edited' y, si el usuario filtró, unimos con filas no filtradas:
        if (prioridad != "(Todas)") or (estado != "(Todas)"):
            # Reinsertamos filas no mostradas para no perderlas
            mask = df.index.isin(fdf.index)
            base = pd.concat([df[~mask], edited], ignore_index=True)
        else:
            base = edited

        # Asegurar todas las columnas en orden
        for c in headers:
            if c not in base.columns:
                base[c] = pd.NA
        base = base[headers]

        ws.clear()
        set_with_dataframe(ws, base, row=1, include_index=False, include_column_header=True)
        st.success("¡Cambios guardados en Google Sheets!")
        st.rerun()

# ---- KPIs mínimos para verificar ejecución ----
st.subheader("KPIs rápidos (demo)")
hoy = pd.Timestamp.today().date()
kpi1 = 0.0
if not df.empty and "Fecha Vencimiento" in df.columns and "Monto en S/" in df.columns:
    kpi1 = df.loc[df["Fecha Vencimiento"]==hoy, "Monto en S/"].fillna(0).sum()
st.metric("Suma de pagos de HOY (S/)", f"{kpi1:,.2f}")
st.caption("Cuando confirmemos que carga, añadimos los 5 KPIs completos y formato final.")
