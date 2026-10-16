"""
Pruebas de las reglas de limpieza. Para correrlas:
    pip install pytest
    pytest -v
"""

import pandas as pd
import pytest

import limpieza as lz

# Tres filas con el mismo formato del portal (datos inventados)
MUESTRA = (
    "numPatent|desEstabl|fecAproba|desActivi|numPatLi|mapa|dirLocCo|numSector|nomComple|nomDistri|\n"
    "1|SODA LA ESQUINA|04/12/2023 00:00:00|RESTAURANTE|7449|1|LOCAL 1 |328|INVERSIONES X SOCIEDAD ANONIMA   |POZOS|\n"
    "2||03/01/2017 00:00:00|VENTA DE BISUTERIA  Y JOYERIA.||2|LOCAL 2 |328|PATENTADO FICTICIO 0002|SANTA_ANA|\n"
    "3|\"EL FARO\"|31/02/2019 00:00:00|restaurante.||3|LOCAL 3 |130|3-101-123456 SOCIEDAD ANONIMA|SANTA_ANA|\n"
)


@pytest.fixture
def limpio():
    df = lz.leer_archivo("muestra.csv", MUESTRA.encode("utf-8"))
    datos, bitacora = lz.limpiar(df)
    return datos, bitacora


def test_detecta_el_separador_y_quita_la_columna_fantasma():
    df = lz.leer_archivo("muestra.csv", MUESTRA.encode("utf-8"))
    assert "desActivi" in df.columns
    datos, _ = lz.limpiar(df)
    assert not any(str(c).startswith("Unnamed") for c in datos.columns)


def test_lee_archivos_en_latin1():
    df = lz.leer_archivo("muestra.csv", MUESTRA.encode("latin-1", errors="replace"))
    assert len(df) == 3


def test_misma_actividad_escrita_distinto_queda_igual(limpio):
    datos, _ = limpio
    assert datos.loc[datos["patente"] == "3", "actividad"].item() == "Restaurante"
    assert datos.loc[datos["patente"] == "2", "actividad"].item() == "Venta de bisuteria y joyeria"


def test_nombre_comercial_vacio_y_comillas(limpio):
    datos, _ = limpio
    assert datos.loc[datos["patente"] == "2", "establecimiento"].item() == lz.SIN_NOMBRE
    assert datos.loc[datos["patente"] == "3", "establecimiento"].item() == "EL FARO"


def test_distrito_legible(limpio):
    datos, _ = limpio
    assert set(datos["distrito"]) == {"Pozos", "Santa Ana"}


def test_fechas_dia_primero_y_fecha_imposible(limpio):
    datos, bitacora = limpio
    assert datos.loc[datos["patente"] == "1", "fecha_aprobacion"].item() == pd.Timestamp("2023-12-04")
    assert pd.isna(datos.loc[datos["patente"] == "3", "fecha_aprobacion"].item())  # 31 de febrero
    assert any("1 fecha no era válida" in linea for linea in bitacora)


def test_licores(limpio):
    datos, _ = limpio
    assert datos["tiene_licores"].tolist() == [True, False, False]


@pytest.mark.parametrize("actividad, categoria", [
    ("OFICINA ADMINISTRATIVA DE AGENCIA DE VIAJES.", "Turismo y hospedaje"),  # el orden importa
    ("BARBERIA", "Belleza y bienestar"),                                     # no es un bar
    ("BAR Y RESTAURANTE", "Restaurantes y comida"),
    ("VENTA DE REPUESTOS PARA AUTOMOVILES", "Vehículos y transporte"),       # antes que «venta»
    ("VENTA DE ROPA", "Comercio minorista"),
    ("SALÓN DE BELLEZA", "Belleza y bienestar"),                             # con tilde
    ("CRIADERO DE MARIPOSAS", lz.OTROS),
])
def test_categorias(actividad, categoria):
    assert lz.categorizar(actividad) == categoria


@pytest.mark.parametrize("patentado, tipo", [
    ("BBQ CHICKEN OESTE COSTA RICA SOCIEDAD DE RESPONSABILIDAD LIMITADA", "Jurídica (empresa)"),
    ("3-101-576694 SOCIEDAD ANONIMA", "Jurídica (empresa)"),
    ("PASTELERIA FINA DE PARIS LIMITADA", "Jurídica (empresa)"),
    ("PATENTADO FICTICIO 0001", "Física"),
])
def test_tipo_de_persona(patentado, tipo):
    assert lz.tipo_persona(patentado) == tipo


def test_archivo_sin_columnas_de_licencias_da_error_claro():
    df = lz.leer_archivo("otro.csv", b"nombre,edad\nAna,30\n")
    with pytest.raises(KeyError, match="desActivi"):
        lz.limpiar(df)


def test_formato_no_soportado():
    with pytest.raises(ValueError, match="Formato no soportado"):
        lz.leer_archivo("foto.png", b"123")


def test_archivo_de_ejemplo_completo():
    contenido = open("datos_ejemplo_licencias.csv", "rb").read()
    datos, _ = lz.limpiar(lz.leer_archivo("datos_ejemplo_licencias.csv", contenido))
    assert len(datos) == 1500                      # 1512 filas menos 12 duplicadas
    assert (datos["categoria"] == lz.OTROS).mean() < 0.05
