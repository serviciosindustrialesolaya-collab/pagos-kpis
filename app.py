import os
import time
import json
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta

st.set_page_config(page_title="KPIs de Pagos — SIOCORP", page_icon="💸", layout="wide")

# -------------------------
# Google Sheets connection
# -------------------------
# Put your Google Service Account JSON into Streamlit secrets:
#   st.secrets["gcp_service_account"]  (entero, el JSON)
# And the Spreadsheet ID into:
#   st.secrets["SPREADSHEET_ID"]
#
# Cómo obtener:
# 1) Crear proyecto en https://console.cloud.google.com/
# 2) Crear "Service Account" y generar una KEY (JSON)
# 3) Abrir la hoja de Google y COMPARTIR con el email de la service account (rol: Editor)
# 4) Copiar el ID de la hoja (lo que va entre /d/ y /edit en la URL)
# 5) En Streamlit Cloud, ir a "Settings → Secrets" y pegar:
#    {{
#      "gcp_service_account": {{ ...contenido del JSON... }},
#      "SPREADSHEET_ID": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#    }}
#
SHEET_NAME = "Pagos"

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(info, scopes=[
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ])
    gc = gspread.authorize(creds)
    return gc

def open_sheet():
    gc = get_gspread_client()
    sh = gc.open_by_key(st.secrets["SPREADSHEET_ID"])
    try:
        ws = sh.worksheet(SHEET_NAME)
    except gspread.WorksheetNotFound:
        # Create worksheet with headers if not exists
        ws = sh.add_worksheet(title=SHEET_NAME, rows=2000, cols=20)
        headers = ["Fecha Registro","Área","Tipo de Pago","Proveedor","ID Registro","Moneda",
                   "Monto","Tipo Cambio","Monto en S/","Fecha Vencimiento","Prioridad","Estado",
                   "Observaciones","Pagos hoy","Proximos 7 dias"]
        ws.update("A1:O1", [headers])
    return sh, ws

# -------------------------
# Data helpers
# -------------------------
def load_df(ws):
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    df = pd.DataFrame(values[1:], columns=values[0])
    # Normalize types
    for col in ["Monto","Tipo Cambio","Monto en S/"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].replace("", "0"), errors="coerce").fillna(0.0)
    for col in ["Fecha Registro","Fecha Vencimiento"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def save_df(ws, df):
    # Write whole sheet (simple approach). For small/mid sheets this is ok.
    df_out = df.copy()
    # Convert dates to strings
    for col in ["Fecha Registro","Fecha Vencimiento"]:
        if col in df_out.columns:
            df_out[col] = df_out[col].dt.strftime("%Y-%m-%d")
    ws.batch_clear(["A2:O200000"])
    if len(df_out):
        ws.update("A2", df_out.values.tolist())
    # Resize to content
    ws.resize(rows=max(100, len(df_out) + 10))

# -------------------------
# UI
# -------------------------
st.markdown("""<style>
:root { --bg:#0b1020; --card:#101935; --ink:#e8ecff; --accent:#f7c948; --muted:#a7b0d6; }
.block-container { padding-top:1.2rem; padding-bottom:1.2rem; }
.kpi-card { background:var(--card); padding:16px; border-radius:16px; border:1px solid #223056; }
.kpi-title { background:var(--accent); color:#222; font-weight:700; padding:8px 12px; border-radius:10px; display:inline-block; margin-bottom:12px; }
.kpi-table { border-collapse:collapse; width:100%; }
.kpi-table th { background:#e8eef9; color:#111; padding:6px 8px; border:1px solid #cfd7ea; text-align:left; }
.kpi-table td { padding:6px 8px; border:1px solid #2b3658; }
</style>
""", unsafe_allow_html=True)

st.title("💸 KPIs de Pagos — SIOCORP")
st.caption("Edición colaborativa (4+ usuarios) en tiempo real. Fuente de datos: Google Sheets.")

sh, ws = open_sheet()
df = load_df(ws)

# Sidebar filters
st.sidebar.header("Filtros")
prioridad = st.sidebar.selectbox("Prioridad", options=["(Todas)"] + sorted(df["Prioridad"].dropna().unique().tolist()) if "Prioridad" in df else ["(Todas)"])
estado = st.sidebar.selectbox("Estado", options=["(Todas)"] + sorted(df["Estado"].dropna().unique().tolist()) if "Estado" in df else ["(Todas)"])

# Quick actions
col_actions = st.columns([1,1,2])
with col_actions[0]:
    if st.button("🔄 Refrescar datos", use_container_width=True):
        df = load_df(ws)
with col_actions[1]:
    if st.button("💾 Guardar cambios (tabla editable)", use_container_width=True, type="primary"):
        try:
            edited = st.session_state.get("edited_df")
            if edited is not None:
                save_df(ws, edited)
                st.success("Cambios guardados en Google Sheets.")
                df = load_df(ws)
            else:
                st.info("No hay cambios para guardar.")
        except Exception as e:
            st.error(f"Error al guardar: {e}")

# Editable table
st.subheader("Base de Datos — Pagos")
if df.empty:
    st.info("La hoja está vacía. Usa el formulario para añadir el primer registro.")
else:
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="edited_df",
        column_config={
            "Monto": st.column_config.NumberColumn(format="%.2f"),
            "Tipo Cambio": st.column_config.NumberColumn(format="%.4f"),
            "Monto en S/": st.column_config.NumberColumn(format="%.2f"),
            "Fecha Registro": st.column_config.DateColumn(format="YYYY-MM-DD"),
            "Fecha Vencimiento": st.column_config.DateColumn(format="YYYY-MM-DD"),
        },
    )

with st.expander("➕ Agregar registro"):
    with st.form("add_form"):
        cols = st.columns(4)
        fecha_reg = cols[0].date_input("Fecha Registro", value=pd.Timestamp.today())
        area = cols[1].text_input("Área")
        tipo_pago = cols[2].text_input("Tipo de Pago")
        proveedor = cols[3].text_input("Proveedor")

        cols2 = st.columns(4)
        id_reg = cols2[0].text_input("ID Registro")
        moneda = cols2[1].selectbox("Moneda", options=["S/","USD"])
        monto = cols2[2].number_input("Monto", min_value=0.0, step=0.01)
        tc = cols2[3].number_input("Tipo Cambio", min_value=0.0, step=0.0001, value=0.0)

        cols3 = st.columns(4)
        monto_s = cols3[0].number_input("Monto en S/", min_value=0.0, step=0.01)
        fecha_v = cols3[1].date_input("Fecha Vencimiento", value=pd.Timestamp.today())
        prioridad_in = cols3[2].selectbox("Prioridad", options=["Alta","Media","Baja"])
        estado_in = cols3[3].selectbox("Estado", options=["Pendiente","Pagado"])

        obs = st.text_area("Observaciones", height=60)
        pagos_hoy = st.checkbox("Pagos hoy?")
        prox_7 = st.checkbox("Próximos 7 días?")

        submitted = st.form_submit_button("Agregar registro")
        if submitted:
            new_row = {
                "Fecha Registro": pd.to_datetime(fecha_reg),
                "Área": area,
                "Tipo de Pago": tipo_pago,
                "Proveedor": proveedor,
                "ID Registro": id_reg,
                "Moneda": moneda,
                "Monto": monto,
                "Tipo Cambio": tc,
                "Monto en S/": monto_s,
                "Fecha Vencimiento": pd.to_datetime(fecha_v),
                "Prioridad": prioridad_in,
                "Estado": estado_in,
                "Observaciones": obs,
                "Pagos hoy": "Sí" if pagos_hoy else "No",
                "Proximos 7 dias": "Sí" if prox_7 else "No",
            }
            df_new = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            try:
                save_df(ws, df_new)
                st.success("Registro agregado.")
                st.rerun()
            except Exception as e:
                st.error(f"Error al agregar: {e}")

# Apply filters for KPI
df_kpi = df.copy()
if "Fecha Vencimiento" in df_kpi:
    df_kpi["Fecha Vencimiento"] = pd.to_datetime(df_kpi["Fecha Vencimiento"], errors="coerce")

if prioridad != "(Todas)" and "Prioridad" in df_kpi:
    df_kpi = df_kpi[df_kpi["Prioridad"] == prioridad]
if estado != "(Todas)" and "Estado" in df_kpi:
    df_kpi = df_kpi[df_kpi["Estado"] == estado]

today = pd.Timestamp.today().normalize()

def fmt_money(x):
    try:
        return f"{x:,.2f}"
    except:
        return x

# KPI 1: pagos de hoy por proveedor
kpi1 = df_kpi[df_kpi["Fecha Vencimiento"]==today] if "Fecha Vencimiento" in df_kpi else pd.DataFrame()
kpi1_grp = kpi1.groupby("Proveedor", dropna=True).agg(**{"Suma de Monto":("Monto","sum"),
                                                         "Suma de Monto en S/":("Monto en S/","sum")}).reset_index() if not kpi1.empty else pd.DataFrame(columns=["Proveedor","Suma de Monto","Suma de Monto en S/"])

# KPI 2: próximos 7 días
if "Fecha Vencimiento" in df_kpi:
    mask7 = (df_kpi["Fecha Vencimiento"]>today) & (df_kpi["Fecha Vencimiento"]<=today+pd.Timedelta(days=7))
    kpi2 = df_kpi[mask7]
else:
    kpi2 = pd.DataFrame()
kpi2_grp = kpi2.groupby("Proveedor", dropna=True).agg(**{"Suma de Monto":("Monto","sum"),
                                                         "Suma de Monto en S/":("Monto en S/","sum")}).reset_index() if not kpi2.empty else pd.DataFrame(columns=["Proveedor","Suma de Monto","Suma de Monto en S/"])

# KPI 3: próximos 30 días por moneda
if "Fecha Vencimiento" in df_kpi:
    mask30 = (df_kpi["Fecha Vencimiento"]>today) & (df_kpi["Fecha Vencimiento"]<=today+pd.Timedelta(days=30))
    kpi3 = df_kpi[mask30]
else:
    kpi3 = pd.DataFrame()
kpi3_grp = kpi3.groupby("Moneda", dropna=True).agg(**{"Suma de Monto":("Monto","sum"),
                                                      "Suma de Monto en S/":("Monto en S/","sum")}).reset_index() if not kpi3.empty else pd.DataFrame(columns=["Moneda","Suma de Monto","Suma de Monto en S/"])

# KPI 4: total por estado
kpi4_grp = df.groupby("Estado", dropna=True).agg(**{"Suma de Monto":("Monto","sum"),
                                                    "Suma de Monto en S/":("Monto en S/","sum")}).reset_index() if not df.empty else pd.DataFrame(columns=["Estado","Suma de Monto","Suma de Monto en S/"])

# KPI 5: pagos por proveedor (Pendiente)
kpi5 = df[df["Estado"]=="Pendiente"] if "Estado" in df else pd.DataFrame(columns=df.columns)
kpi5_grp = kpi5.groupby("Proveedor", dropna=True).agg(**{"Suma de Monto":("Monto","sum"),
                                                         "Suma de Monto en S/":("Monto en S/","sum")}).reset_index() if not kpi5.empty else pd.DataFrame(columns=["Proveedor","Suma de Monto","Suma de Monto en S/"])

# Render KPIs
st.markdown("### Indicadores (KPI)")
colA, colB = st.columns(2)

def render_table(df_in, title):
    st.markdown(f'<div class="kpi-card"><div class="kpi-title">{title}</div>', unsafe_allow_html=True)
    if df_in is None or len(df_in)==0:
        st.info("Sin datos.")
    else:
        df_show = df_in.copy()
        for col in ["Suma de Monto","Suma de Monto en S/"]:
            if col in df_show.columns:
                df_show[col] = df_show[col].map(fmt_money)
        st.table(df_show)
    st.markdown("</div>", unsafe_allow_html=True)

with colA:
    render_table(kpi1_grp, "KPI 1 — Pagos del día (por proveedor)")
    render_table(kpi3_grp, "KPI 3 — Pagos próximos (30 días) por moneda")
with colB:
    render_table(kpi2_grp, "KPI 2 — Pagos próximos (7 días) por proveedor")
    render_table(kpi4_grp, "KPI 4 — Total pagado y pendiente")
    render_table(kpi5_grp, "KPI 5 — Pagos por proveedor (Pendiente)")

st.caption("Consejo: usa el botón 'Refrescar datos' si varios usuarios están editando a la vez.")
