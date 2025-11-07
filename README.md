# KPIs de Pagos — App colaborativa (gratis)

**Tecnologías:** Streamlit (Python) + Google Sheets como base de datos.  
Soporta 4+ usuarios simultáneos sin servidor propio.

## Deploy gratis en Streamlit Cloud
1. Sube estos archivos a un repositorio en **GitHub** (público está bien).
2. Ve a https://share.streamlit.io/ e inicia sesión con tu cuenta.
3. Crea una nueva app apuntando a `app.py` en tu repo.
4. En **Settings → Secrets**, pega algo como:

```
{
  "gcp_service_account": {
    ...PEGA AQUÍ EL JSON COMPLETO DE TU SERVICE ACCOUNT...
  },
  "SPREADSHEET_ID": "TU_ID_DE_SHEET"
}
```

> **Importante:** Comparte tu Google Sheet con el correo de la Service Account (rol **Editor**).

## Estructura de la Hoja
Crea una hoja llamada **Pagos** con estos encabezados en la fila 1:
```
Fecha Registro, Área, Tipo de Pago, Proveedor, ID Registro, Moneda, Monto, Tipo Cambio, Monto en S/, Fecha Vencimiento, Prioridad, Estado, Observaciones, Pagos hoy, Proximos 7 dias
```

La app creará la hoja si no existe.

## KPIs
- **KPI 1:** Pagos del día por proveedor
- **KPI 2:** Próximos 7 días por proveedor
- **KPI 3:** Próximos 30 días por moneda
- **KPI 4:** Total pagado y pendiente
- **KPI 5:** Pagos por proveedor (Pendiente)

## Edición colaborativa
- Tabla editable + formulario para agregar registros
- Botón **Guardar cambios** escribe en la hoja
- Botón **Refrescar** carga cambios de otros usuarios
