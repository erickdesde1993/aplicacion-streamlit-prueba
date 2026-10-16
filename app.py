"""
app.py — Tablero de licencias comerciales.

Suba el archivo de licencias (como el del portal de datos abiertos de la
Municipalidad de Santa Ana), la app lo limpia y arma un tablero interactivo.

    pip install -r requirements.txt
    streamlit run app.py

Python Express II · Profesor Erick Vargas Víctor
"""

import zipfile
from pathlib import Path

import pandas as pd
import streamlit as st

import graficos as g
import limpieza as lz

EJEMPLO = Path(__file__).parent / "datos_ejemplo_licencias.csv"

st.set_page_config(page_title="Licencias comerciales", page_icon="🏪", layout="wide")


@st.cache_data(show_spinner="Limpiando el archivo...")
def procesar(nombre: str, contenido: bytes):
    return lz.limpiar(lz.leer_archivo(nombre, contenido))


def conteo(df: pd.DataFrame, campo: str, top: int | None = None) -> pd.DataFrame:
    c = df[campo].value_counts().rename_axis(campo).reset_index(name="licencias")
    c["porcentaje"] = c["licencias"] / max(len(df), 1)
    return c.head(top) if top else c


def usar_ejemplo(valor: bool):
    st.session_state["ejemplo"] = valor


# ----------------------------------------------------------------------
# Encabezado y carga
# ----------------------------------------------------------------------
st.title("🏪 Tablero de licencias comerciales")
st.markdown(
    "Suba el archivo de licencias comerciales del cantón (formato del portal de datos abiertos: "
    "columnas separadas por «|»). La app lo **limpia**, lo **normaliza** y le arma un **tablero** "
    "con las actividades comerciales."
)

archivo = st.file_uploader("Seleccione el archivo de licencias", type=["csv", "txt", "xlsx"],
                           help="CSV o TXT separado por | ; , o tabulador, o un Excel con las mismas columnas.")

if archivo is None and not st.session_state.get("ejemplo"):
    st.info("👆 Suba su archivo, o explore primero el tablero con datos de ejemplo.")
    st.button("Probar con datos de ejemplo (ficticios)", type="primary", on_click=usar_ejemplo, args=(True,))
    with st.expander("¿Qué columnas necesita el archivo?"):
        st.markdown(
            "Las del portal de datos abiertos: `numPatent`, `desEstabl`, `fecAproba`, `desActivi`, `numPatLi`, "
            "`mapa`, `dirLocCo`, `numSector`, `nomComple` y `nomDistri`. Las únicas obligatorias son "
            "`desActivi` (actividad) y `nomDistri` (distrito)."
        )
    with st.expander("🔒 ¿Qué pasa con mis datos?"):
        st.write("El archivo se procesa en memoria mientras usa la página y no se guarda en ningún lado.")
    st.stop()

if archivo is None:
    nombre, contenido = EJEMPLO.name, EJEMPLO.read_bytes()
    st.warning("🧪 Está viendo **datos de ejemplo ficticios**: ningún comercio ni persona es real.")
    st.button("Quitar el ejemplo", on_click=usar_ejemplo, args=(False,))
else:
    usar_ejemplo(False)
    nombre, contenido = archivo.name, archivo.getvalue()

try:
    datos, bitacora = procesar(nombre, contenido)
except (ValueError, KeyError) as error:
    st.error(f"❌ {str(error).strip(chr(39))}")
    st.stop()
except pd.errors.ParserError:
    st.error("❌ No se pudo interpretar el archivo. Revise que todas las filas tengan la misma cantidad de columnas.")
    st.stop()
except zipfile.BadZipFile:
    st.error("❌ El Excel parece dañado. Ábralo y guárdelo de nuevo como .xlsx.")
    st.stop()

if datos.empty:
    st.warning("El archivo se leyó, pero no tiene licencias.")
    st.stop()

# ----------------------------------------------------------------------
# Filtros (barra lateral)
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("🔎 Filtros")
    distritos = sorted(datos["distrito"].unique())
    sel_distritos = st.multiselect("Distritos", distritos, default=distritos)
    categorias = datos["categoria"].value_counts().index.tolist()
    sel_categorias = st.multiselect("Categorías", categorias, default=categorias)

    anios = datos["anio"].dropna()
    if not anios.empty and anios.min() < anios.max():
        rango = st.slider("Año de aprobación", int(anios.min()), int(anios.max()), (int(anios.min()), int(anios.max())))
    else:
        rango = None
    sin_fecha = st.checkbox("Incluir licencias sin fecha válida", value=True)
    solo_licores = st.toggle("Solo con patente de licores", value=False)
    buscar = st.text_input("Buscar comercio o actividad", placeholder="Ej.: soda, ferretería, Lindora")

filtro = datos["distrito"].isin(sel_distritos) & datos["categoria"].isin(sel_categorias)
if rango:
    en_rango = datos["anio"].between(*rango)
    filtro &= en_rango.fillna(False) | (datos["anio"].isna() & sin_fecha)
if solo_licores:
    filtro &= datos["tiene_licores"]
if buscar.strip():
    texto = lz.clave(buscar)
    filtro &= (datos["establecimiento"].map(lz.clave).str.contains(texto, regex=False)
               | datos["actividad"].map(lz.clave).str.contains(texto, regex=False))
vista = datos[filtro.fillna(False)]

if vista.empty:
    st.warning("Ninguna licencia cumple con los filtros. Pruebe ampliando la selección.")
    st.stop()

# ----------------------------------------------------------------------
# Indicadores
# ----------------------------------------------------------------------
fecha_max = datos["fecha_aprobacion"].max()
ultimo_anio = vista[vista["fecha_aprobacion"] > fecha_max - pd.DateOffset(years=1)] if pd.notna(fecha_max) else vista.iloc[0:0]
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Licencias", f"{len(vista):,}", help=f"De {len(datos):,} en el archivo")
k2.metric("Actividades distintas", f"{vista['actividad'].nunique():,}")
k3.metric("Aprobadas en el último año", f"{len(ultimo_anio):,}",
          help=f"12 meses antes de la fecha más reciente del archivo ({fecha_max:%d/%m/%Y})" if pd.notna(fecha_max) else None)
k4.metric("Con patente de licores", f"{vista['tiene_licores'].mean():.0%}")
k5.metric("Patentadas por empresas", f"{(vista['tipo_persona'] == 'Jurídica (empresa)').mean():.0%}")

tab_pan, tab_act, tab_ten, tab_dis, tab_dat, tab_lim = st.tabs(
    ["📊 Panorama", "🏷️ Actividades", "📈 Tendencia", "🗺️ Distritos", "📋 Datos", "🧹 Limpieza"])

# ----------------------------------------------------------------------
# Panorama
# ----------------------------------------------------------------------
with tab_pan:
    por_cat = conteo(vista, "categoria")
    por_dis = conteo(vista, "distrito")
    top_act = conteo(vista, "actividad", 1).iloc[0]

    hallazgos = [
        f"**{por_cat.iloc[0]['categoria']}** es la categoría con más licencias: "
        f"{por_cat.iloc[0]['licencias']:,} ({por_cat.iloc[0]['porcentaje']:.0%}).",
        f"**{por_dis.iloc[0]['distrito']}** concentra la mayor actividad comercial: "
        f"{por_dis.iloc[0]['licencias']:,} licencias ({por_dis.iloc[0]['porcentaje']:.0%}).",
        f"La actividad individual más común es **{top_act['actividad'].lower()}**, con {top_act['licencias']:,} licencias.",
    ]
    por_anio = vista.dropna(subset=["anio"]).groupby("anio").size()
    ultimo_completo = (fecha_max.year if fecha_max.month == 12 else fecha_max.year - 1) if pd.notna(fecha_max) else None
    if ultimo_completo in por_anio.index and (ultimo_completo - 1) in por_anio.index:
        actual, previo = por_anio[ultimo_completo], por_anio[ultimo_completo - 1]
        cambio = actual / previo - 1
        hallazgos.append(
            f"En **{ultimo_completo}** se aprobaron {actual:,} licencias, "
            f"{abs(cambio):.0%} {'más' if cambio >= 0 else 'menos'} que en {ultimo_completo - 1}.")
    st.markdown("#### 💡 Hallazgos")
    st.markdown("\n".join(f"- {h}" for h in hallazgos))

    c1, c2 = st.columns(2)
    c1.altair_chart(g.barras_horizontales(por_cat, "categoria", "Licencias por categoría", "Categoría"),
                    width="stretch")
    c2.altair_chart(g.barras_horizontales(por_dis, "distrito", "Licencias por distrito", "Distrito"),
                    width="stretch")
    c3, c4 = st.columns(2)
    c3.altair_chart(g.barras_horizontales(conteo(vista, "tipo_persona"), "tipo_persona",
                                          "¿Quién tiene la licencia?", "Tipo de patentado"), width="stretch")
    licores = vista["tiene_licores"].map({True: "Con patente de licores", False: "Sin patente de licores"})
    c4.altair_chart(g.barras_horizontales(conteo(vista.assign(licores=licores), "licores"), "licores",
                                          "Patente de licores", "Licores"), width="stretch")

# ----------------------------------------------------------------------
# Actividades
# ----------------------------------------------------------------------
with tab_act:
    n = st.slider("¿Cuántas actividades mostrar?", 5, 40, 15)
    top = conteo(vista, "actividad", n)
    st.altair_chart(g.barras_horizontales(top, "actividad", f"Las {len(top)} actividades con más licencias", "Actividad"),
                    width="stretch")
    resumen = (vista.groupby(["actividad", "categoria"])
                    .agg(licencias=("actividad", "size"), con_licores=("tiene_licores", "mean"))
                    .reset_index().sort_values("licencias", ascending=False))
    resumen["porcentaje"] = resumen["licencias"] / len(vista)
    st.dataframe(resumen, hide_index=True, width="stretch", column_config={
        "actividad": "Actividad", "categoria": "Categoría", "licencias": st.column_config.NumberColumn("Licencias", format="%d"),
        "porcentaje": st.column_config.ProgressColumn("% del total", format="percent", min_value=0, max_value=float(resumen["porcentaje"].max())),
        "con_licores": st.column_config.NumberColumn("Con licores", format="percent"),
    })

# ----------------------------------------------------------------------
# Tendencia
# ----------------------------------------------------------------------
with tab_ten:
    con_fecha = vista.dropna(subset=["anio"])
    if con_fecha.empty:
        st.info("El archivo no tiene fechas de aprobación válidas.")
    else:
        anual = con_fecha.groupby("anio").size().reset_index(name="licencias")
        anual["anio"] = anual["anio"].astype(int)
        incompleto = None
        if pd.notna(fecha_max) and fecha_max.month < 12 and fecha_max.year in set(anual["anio"]):
            incompleto = int(fecha_max.year)
            st.caption(f"ℹ️ El archivo llega hasta el {fecha_max:%d/%m/%Y}: {incompleto} está incompleto (barra más clara).")
        st.altair_chart(g.columnas_por_anio(anual, "Licencias aprobadas por año", incompleto), width="stretch")

        top5 = con_fecha["categoria"].value_counts().index[:5].tolist()
        desde = st.slider("Comparar categorías desde el año", int(anual["anio"].min()), int(anual["anio"].max()),
                          max(int(anual["anio"].min()), int(anual["anio"].max()) - 10))
        por_cat_anio = (con_fecha[con_fecha["categoria"].isin(top5) & (con_fecha["anio"] >= desde)]
                        .groupby(["anio", "categoria"]).size().reset_index(name="licencias"))
        por_cat_anio["anio"] = por_cat_anio["anio"].astype(int)
        st.altair_chart(g.lineas_por_categoria(por_cat_anio, top5, "Las 5 categorías principales, año por año"),
                        width="stretch")
        with st.expander("Ver la tabla de este gráfico"):
            tabla = por_cat_anio.pivot(index="anio", columns="categoria", values="licencias").fillna(0).astype(int)
            st.dataframe(tabla[top5], width="stretch")

# ----------------------------------------------------------------------
# Distritos
# ----------------------------------------------------------------------
with tab_dis:
    cruce = vista.groupby(["distrito", "categoria"]).size().reset_index(name="licencias")
    completo = pd.MultiIndex.from_product([cruce["distrito"].unique(), cruce["categoria"].unique()],
                                          names=["distrito", "categoria"])
    cruce = cruce.set_index(["distrito", "categoria"]).reindex(completo, fill_value=0).reset_index()
    st.altair_chart(g.mapa_de_calor(cruce, "¿Qué tipo de comercio hay en cada distrito?"), width="stretch")
    st.caption("Más oscuro = más licencias. Pase el mouse sobre una celda para ver el detalle.")

# ----------------------------------------------------------------------
# Datos
# ----------------------------------------------------------------------
with tab_dat:
    mostrar_nombres = st.checkbox("Mostrar el nombre del patentado", value=False,
                                  help="Puede ser una persona física. Muéstrelo solo si es necesario.")
    columnas = ["patente", "establecimiento", "actividad", "categoria", "distrito", "fecha_aprobacion",
                "tiene_licores", "tipo_persona", "direccion"]
    if mostrar_nombres and "patentado" in vista.columns:
        columnas.insert(2, "patentado")
    columnas = [c for c in columnas if c in vista.columns]
    st.dataframe(vista[columnas], hide_index=True, width="stretch", column_config={
        "fecha_aprobacion": st.column_config.DateColumn("Fecha de aprobación", format="DD/MM/YYYY"),
        "tiene_licores": st.column_config.CheckboxColumn("Licores"),
        "tipo_persona": "Tipo de patentado", "establecimiento": "Establecimiento", "actividad": "Actividad",
        "categoria": "Categoría", "distrito": "Distrito", "direccion": "Dirección", "patente": "Patente",
        "patentado": "Patentado",
    })
    base = Path(nombre).stem + "_limpio"
    d1, d2 = st.columns(2)
    d1.download_button(f"⬇️ Descargar CSV ({len(vista):,} filas filtradas)", lz.a_csv_bytes(vista[columnas]),
                       f"{base}.csv", "text/csv", width="stretch", type="primary")
    d2.download_button("⬇️ Descargar Excel", lz.a_excel_bytes(vista[columnas]), f"{base}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")

# ----------------------------------------------------------------------
# Limpieza
# ----------------------------------------------------------------------
with tab_lim:
    st.markdown("#### 🧹 Lo que se hizo con su archivo")
    for paso, cambio in enumerate(bitacora, start=1):
        st.markdown(f"**{paso}.** {cambio}")
    otros = datos.loc[datos["categoria"] == lz.OTROS, "actividad"].value_counts()
    if not otros.empty:
        st.markdown("#### 🤔 Actividades que quedaron en «Otros»")
        st.caption("Para clasificarlas, agregue una palabra clave en la lista CATEGORIAS de limpieza.py.")
        st.dataframe(otros.rename_axis("Actividad").reset_index(name="Licencias"), hide_index=True, width="stretch")

st.caption("Python Express II · Datos: archivo subido por la persona usuaria · Hecho con pandas, Altair y Streamlit")
