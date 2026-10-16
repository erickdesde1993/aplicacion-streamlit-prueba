"""
graficos.py — Los gráficos del tablero, hechos con Altair (viene incluido con Streamlit).

Reglas de diseño que siguen todos:
- Una sola serie = un solo color, sin leyenda (el título dice qué es).
- Barras delgadas con la punta redondeada y el valor escrito al final.
- Cuadrícula suave, para que mande el dato y no el fondo.
- Al pasar el mouse, cada barra, punto o celda muestra su detalle.
"""

import altair as alt
import pandas as pd

AZUL = "#2a78d6"            # color de la serie única
TEXTO = "#52514e"           # texto secundario (los números nunca van en color de serie)
GRILLA = "#e8e8e6"
# Paleta categórica validada (orden fijo; nunca se reparte por ranking)
CATEGORICA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
# Rampa secuencial de un solo tono (claro = poco, oscuro = mucho)
SECUENCIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]


def _base(chart):
    return (chart.configure_view(strokeWidth=0)
                 .configure_axis(labelColor=TEXTO, titleColor=TEXTO, gridColor=GRILLA, domain=False, tickColor=GRILLA,
                                 labelFontSize=12, titleFontSize=12)
                 .configure_legend(labelColor=TEXTO, titleColor=TEXTO, labelFontSize=12, orient="top")
                 .configure_title(color="#0b0b0b", fontSize=15, anchor="start"))


def barras_horizontales(conteo: pd.DataFrame, campo: str, titulo: str, etiqueta_eje: str = "") -> alt.Chart:
    """conteo: columnas [campo, 'licencias', 'porcentaje'], ya ordenado de mayor a menor."""
    alto = max(110, 32 * len(conteo))
    eje_y = alt.Y(f"{campo}:N", sort="-x", title=None,
                  axis=alt.Axis(labelLimit=280, ticks=False, labelPadding=8, labelOverlap=False))
    eje_x = alt.X("licencias:Q", title=None, axis=alt.Axis(format=",d", tickCount=4, labels=False, grid=False))
    detalle = [alt.Tooltip(f"{campo}:N", title=etiqueta_eje or campo.capitalize()),
               alt.Tooltip("licencias:Q", title="Licencias", format=",d"),
               alt.Tooltip("porcentaje:Q", title="% del total", format=".1%")]
    barras = alt.Chart(conteo).mark_bar(color=AZUL, size=18, cornerRadiusEnd=4).encode(y=eje_y, x=eje_x, tooltip=detalle)
    valores = alt.Chart(conteo).mark_text(align="left", dx=6, color=TEXTO, fontSize=12).encode(
        y=eje_y, x="licencias:Q", text=alt.Text("licencias:Q", format=",d"))
    return _base((barras + valores).properties(title=titulo, height=alto))


def columnas_por_anio(por_anio: pd.DataFrame, titulo: str, anio_incompleto=None) -> alt.Chart:
    """por_anio: columnas ['anio', 'licencias']."""
    datos = por_anio.copy()
    datos["estado"] = "Año completo"
    if anio_incompleto is not None:
        datos.loc[datos["anio"] == anio_incompleto, "estado"] = "Año incompleto"
    detalle = [alt.Tooltip("anio:O", title="Año"), alt.Tooltip("licencias:Q", title="Licencias aprobadas", format=",d"),
               alt.Tooltip("estado:N", title="Dato")]
    barras = alt.Chart(datos).mark_bar(size=16, cornerRadiusEnd=4).encode(
        x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("licencias:Q", title="Licencias aprobadas", axis=alt.Axis(format=",d", tickCount=5)),
        color=alt.condition(alt.datum.estado == "Año incompleto", alt.value("#9ec5f4"), alt.value(AZUL)),
        tooltip=detalle,
    )
    return _base(barras.properties(title=titulo, height=320))


def lineas_por_categoria(datos: pd.DataFrame, categorias: list[str], titulo: str) -> alt.Chart:
    """datos: columnas ['anio', 'categoria', 'licencias']; categorias: máximo 5, en orden fijo."""
    escala = alt.Scale(domain=categorias, range=CATEGORICA[: len(categorias)])
    base = alt.Chart(datos).encode(
        x=alt.X("anio:O", title=None, axis=alt.Axis(labelAngle=0, labelOverlap="greedy")),
        y=alt.Y("licencias:Q", title="Licencias aprobadas", axis=alt.Axis(format=",d", tickCount=5)),
        color=alt.Color("categoria:N", scale=escala, title=None),
        tooltip=[alt.Tooltip("categoria:N", title="Categoría"), alt.Tooltip("anio:O", title="Año"),
                 alt.Tooltip("licencias:Q", title="Licencias", format=",d")],
    )
    lineas = base.mark_line(strokeWidth=2, strokeCap="round", strokeJoin="round")
    puntos = base.mark_point(filled=True, size=50, stroke="white", strokeWidth=2, opacity=1)
    return _base((lineas + puntos).properties(title=titulo, height=340))


def mapa_de_calor(tabla: pd.DataFrame, titulo: str) -> alt.Chart:
    """tabla: columnas ['distrito', 'categoria', 'licencias']."""
    maximo = max(int(tabla["licencias"].max()), 1)
    base = alt.Chart(tabla).encode(
        x=alt.X("distrito:N", title=None, axis=alt.Axis(labelAngle=0, orient="top", ticks=False)),
        y=alt.Y("categoria:N", title=None, sort=alt.EncodingSortField("licencias", op="sum", order="descending"),
                axis=alt.Axis(labelLimit=280, ticks=False, labelOverlap=False)),
    )
    celdas = base.mark_rect(stroke="white", strokeWidth=2, cornerRadius=3).encode(
        color=alt.Color("licencias:Q", scale=alt.Scale(range=SECUENCIAL, domain=[0, maximo]),
                        legend=alt.Legend(title="Licencias", orient="right", format=",d")),
        tooltip=[alt.Tooltip("distrito:N", title="Distrito"), alt.Tooltip("categoria:N", title="Categoría"),
                 alt.Tooltip("licencias:Q", title="Licencias", format=",d")],
    )
    numeros = base.mark_text(fontSize=12).encode(
        text=alt.condition(alt.datum.licencias > 0, alt.Text("licencias:Q", format=",d"), alt.value("")),
        color=alt.condition(alt.datum.licencias > maximo * 0.45, alt.value("white"), alt.value("#0b0b0b")),
    )
    return _base((celdas + numeros).properties(title=titulo, height=max(260, 34 * tabla["categoria"].nunique())))
