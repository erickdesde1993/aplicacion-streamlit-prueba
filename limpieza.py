"""
limpieza.py — Lee, limpia y normaliza el archivo de licencias comerciales.

Pensado para el formato del portal de datos abiertos de la Municipalidad
de Santa Ana (columnas numPatent, desEstabl, fecAproba, desActivi, ...),
separado por "|". Aquí no hay nada de Streamlit: solo pandas y funciones
que se pueden probar por aparte (vea test_limpieza.py).

Python Express II · Profesor Erick Vargas Víctor
"""

from __future__ import annotations

import io
import re
import unicodedata

import pandas as pd

# ----------------------------------------------------------------------
# Columnas: nombre en el archivo original -> nombre legible
# ----------------------------------------------------------------------
COLUMNAS = {
    "numpatent": "patente",
    "desestabl": "establecimiento",
    "fecaproba": "fecha_aprobacion",
    "desactivi": "actividad_original",
    "numpatli": "patente_licores",
    "mapa": "mapa",
    "dirlocco": "direccion",
    "numsector": "sector",
    "nomcomple": "patentado",
    "nomdistri": "distrito",
}
OBLIGATORIAS = ["actividad_original", "distrito"]
NOMBRE_ORIGINAL = {"actividad_original": "desActivi (actividad)", "distrito": "nomDistri (distrito)"}

SIN_NOMBRE = "(Sin nombre comercial)"
SIN_DATO = "(Sin dato)"

# ----------------------------------------------------------------------
# Categorías de actividad. El ORDEN importa: gana la primera que calce.
# Por ejemplo, "Oficina administrativa de agencia de viajes" es Turismo,
# no Oficinas, porque Turismo se revisa antes.
# Cada patrón es una expresión regular sobre el texto en MAYÚSCULAS y
# sin tildes. \b marca el inicio de palabra: \bBAR no calza con BARBERIA.
# ----------------------------------------------------------------------
CATEGORIAS: list[tuple[str, list[str]]] = [
    ("Turismo y hospedaje", [r"\bHOTEL", r"HOSPEDAJE", r"\bCABINA", r"AGENCIA DE VIAJE", r"\bTOUR", r"TURIS",
                             r"ALQUILER DE HABITACION", r"APARTOTEL", r"\bHOSTAL"]),
    ("Educación", [r"ESCUELA", r"COLEGIO", r"EDUCA", r"ACADEMIA", r"INSTITUTO", r"ENSENANZA", r"GUARDERIA",
                   r"\bKINDER", r"PREESCOLAR", r"IDIOMA", r"\bCLASES", r"\bCUIDO"]),
    ("Salud", [r"CLINICA", r"CONSULTORIO", r"MEDIC", r"ODONTO", r"DENTAL", r"FARMACIA", r"OPTICA",
               r"LABORATORIO CLINICO", r"FISIOTERAPIA", r"PSICOLOG", r"NUTRICI", r"VETERINAR", r"HOSPITAL"]),
    ("Belleza y bienestar", [r"SALON DE BELLEZA", r"BELLEZA", r"ESTETICA", r"BARBER", r"PELUQUER", r"\bUNAS",
                             r"MANICUR", r"\bSPA\b", r"GIMNASIO", r"\bGYM", r"YOGA", r"MASAJE"]),
    ("Restaurantes y comida", [r"RESTAURA", r"\bSODA", r"CAFETERIA", r"\bCAFE", r"PANADER", r"PASTELER",
                               r"REPOSTER", r"PIZZ", r"HELAD", r"COMIDA", r"\bBAR\b", r"CANTINA", r"SUSHI",
                               r"CATERING", r"MARISQUER", r"FOOD", r"GRILL", r"BOCADILLO"]),
    ("Supermercados y abarrotes", [r"SUPERMERCADO", r"MINI ?SUPER", r"ABASTECEDOR", r"PULPERIA", r"VERDULER",
                                   r"FRUTER", r"CARNICER", r"ABARROTE", r"LICORERA", r"MERCADO"]),
    ("Vehículos y transporte", [r"TALLER MECANIC", r"MECANIC", r"\bAUTO", r"VEHICUL", r"LAVACAR", r"LAVA CAR",
                                r"REPUESTO", r"LLANTA", r"TRANSPORTE", r"RENT A CAR", r"GASOLINERA",
                                r"ESTACION DE SERVICIO", r"PARQUEO", r"MOTOCICLET"]),
    ("Construcción e inmobiliaria", [r"CONSTRUC", r"BIENES RAICES", r"INMOBILIAR", r"ALQUILER DE LOCAL",
                                     r"ALQUILER DE OFICINA", r"BODEGA", r"DEPOSITO", r"CONDOMINIO",
                                     r"MATERIALES", r"FERRETER", r"DESARROLLADOR"]),
    ("Industria y manufactura", [r"FABRICA", r"INDUSTRI", r"MANUFACTUR", r"PRODUCCION", r"PLANTA PROCESADORA",
                                 r"EMBOTELLA", r"IMPRENTA"]),
    ("Oficinas y servicios profesionales", [r"OFICINA", r"ADMINISTRATIV", r"CONSULTOR", r"ASESOR", r"ABOGAD",
                                            r"NOTAR", r"CONTAB", r"ARQUITECT", r"INGENIER", r"SOFTWARE",
                                            r"TECNOLOG", r"PUBLICIDAD", r"MARKETING", r"CORREDOR", r"SEGURO",
                                            r"FINANCIER", r"BANCO", r"SERVICIOS PROFESIONALES", r"CALL CENTER"]),
    ("Comercio minorista", [r"VENTA", r"TIENDA", r"BAZAR", r"BOUTIQUE", r"\bROPA", r"CALZADO", r"ZAPAT",
                            r"JOYER", r"BISUTER", r"LIBRER", r"MUEBLE", r"ELECTRODOMEST", r"FLORISTER",
                            r"JUGUETER", r"PERFUMER", r"ARTICULOS", r"DISTRIBU", r"IMPORTA", r"COMERCIO"]),
]
OTROS = "Otros"

# Palabras que indican que el patentado es una persona jurídica (empresa)
PATRON_JURIDICA = re.compile(
    r"SOCIEDAD|\bS\.?\s?A\.?$|\bS\.?\s?A\.?\s|LIMITADA|\bLTDA|\bS\.?R\.?L|EMPRESA INDIVIDUAL|E\.?I\.?R\.?L"
    r"|ASOCIACION|FUNDACION|COOPERATIVA|CORPORACION|\bINC\b|\bLLC\b|\bCORP\b|^\d-?\d{3}-?\d{6}"
)

# Valores que en la práctica significan "no hay dato"
VACIOS = {"", "NAN", "NONE", "NULL", "N/A", "NA", "-", "--", "0"}


# ----------------------------------------------------------------------
# 1. Lectura
# ----------------------------------------------------------------------

def leer_archivo(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Lee CSV/TXT (separador | , ; o tabulador) o Excel, todo como texto."""
    if not contenido:
        raise ValueError("El archivo está vacío.")
    nombre = nombre.lower()

    if nombre.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(io.BytesIO(contenido), dtype=str, keep_default_na=False)

    if nombre.endswith((".csv", ".txt")):
        for codificacion in ("utf-8-sig", "latin-1"):
            try:
                texto = contenido.decode(codificacion)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError("No se pudo leer el texto del archivo (codificación desconocida).")
        primera = texto.splitlines()[0] if texto.strip() else ""
        separador = max(["|", ";", ",", "\t"], key=primera.count)
        if primera.count(separador) == 0:
            raise ValueError("No se encontró un separador de columnas (| ; , o tabulador).")
        return pd.read_csv(io.StringIO(texto), sep=separador, dtype=str, keep_default_na=False)

    raise ValueError("Formato no soportado. Suba un archivo .csv, .txt o .xlsx.")


# ----------------------------------------------------------------------
# 2. Funciones pequeñas de limpieza
# ----------------------------------------------------------------------

def plural(n: int, singular: str, plural_: str) -> str:
    return f"{n} {singular if n == 1 else plural_}"


def sin_tildes(texto: str) -> str:
    normal = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normal if not unicodedata.combining(c))


def limpiar_texto(serie: pd.Series) -> pd.Series:
    """Quita comillas sobrantes y espacios de más; los vacíos quedan como NA."""
    s = serie.astype("string").str.strip().str.strip('"').str.strip("'")
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    return s.mask(s.str.upper().isin(VACIOS))


def clave(texto: str) -> str:
    """Forma de comparar textos: MAYÚSCULAS, sin tildes, sin puntuación final."""
    t = sin_tildes(str(texto)).upper()
    t = re.sub(r"[.,;:]+$", "", t.strip())
    return re.sub(r"\s+", " ", t)


def a_oracion(texto: str) -> str:
    """'VENTA DE BISUTERIA Y JOYERIA.' -> 'Venta de bisuteria y joyeria'."""
    t = re.sub(r"[.,;:]+$", "", str(texto).strip())
    return t[:1].upper() + t[1:].lower() if t else t


def nombre_distrito(texto) -> str:
    """'SANTA_ANA' -> 'Santa Ana'."""
    if pd.isna(texto):
        return SIN_DATO
    return str(texto).replace("_", " ").strip().title()


def categorizar(actividad) -> str:
    if pd.isna(actividad):
        return OTROS
    t = clave(actividad)
    for categoria, patrones in CATEGORIAS:
        if any(re.search(p, t) for p in patrones):
            return categoria
    return OTROS


def tipo_persona(patentado) -> str:
    if pd.isna(patentado):
        return SIN_DATO
    return "Jurídica (empresa)" if PATRON_JURIDICA.search(clave(patentado)) else "Física"


def a_fecha(serie: pd.Series) -> pd.Series:
    """'04/12/2023 00:00:00' -> 2023-12-04 (el día va primero)."""
    s = serie.astype("string").str.strip()
    fechas = pd.to_datetime(s, format="%d/%m/%Y %H:%M:%S", errors="coerce")
    faltan = fechas.isna() & s.notna()
    if faltan.any():  # otros formatos: 04/12/2023, 2023-12-04, ...
        fechas[faltan] = pd.to_datetime(s[faltan], dayfirst=True, errors="coerce", format="mixed")
    return fechas


# ----------------------------------------------------------------------
# 3. El proceso completo, con bitácora
# ----------------------------------------------------------------------

def limpiar(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Devuelve (datos limpios, bitácora de cambios)."""
    bitacora: list[str] = []
    df = df.copy()

    # Columnas vacías (el "|" al final de cada línea crea una columna fantasma)
    fantasmas = [c for c in df.columns if str(c).startswith("Unnamed") or df[c].astype(str).str.strip().eq("").all()]
    if fantasmas:
        df = df.drop(columns=fantasmas)
        bitacora.append(f"Columnas vacías eliminadas: {len(fantasmas)} (el «|» al final de cada línea crea una).")

    # Renombrar a nombres legibles, sin importar mayúsculas
    mapeo = {c: COLUMNAS[clave(c).lower()] for c in df.columns if clave(c).lower() in COLUMNAS}
    df = df.rename(columns=mapeo)
    faltantes = [c for c in OBLIGATORIAS if c not in df.columns]
    if faltantes:
        raise KeyError(
            "El archivo no tiene las columnas esperadas: falta "
            + ", ".join(NOMBRE_ORIGINAL[c] for c in faltantes)
            + ". ¿Es un archivo de licencias comerciales?"
        )
    bitacora.append(f"Se renombraron {len(mapeo)} columnas a nombres legibles (numPatent → patente, ...).")

    # Texto: espacios, comillas, vacíos disfrazados
    for col in df.columns:
        df[col] = limpiar_texto(df[col])
    bitacora.append("Se quitaron espacios dobles, espacios al final y comillas sobrantes en todas las columnas.")

    # Filas totalmente vacías y duplicados exactos
    antes = len(df)
    df = df.dropna(how="all")
    if antes - len(df):
        bitacora.append(f"Filas vacías eliminadas: {antes - len(df)}.")
    antes = len(df)
    df = df.drop_duplicates()
    if antes - len(df):
        bitacora.append(f"Filas duplicadas eliminadas: {antes - len(df)}.")

    # Nombre comercial faltante
    if "establecimiento" in df.columns:
        sin_nombre = int(df["establecimiento"].isna().sum())
        df["establecimiento"] = df["establecimiento"].fillna(SIN_NOMBRE)
        if sin_nombre:
            bitacora.append(f"{plural(sin_nombre, 'licencia no tenía', 'licencias no tenían')} nombre comercial: "
                            f"se marcaron como «{SIN_NOMBRE}».")
    else:
        df["establecimiento"] = SIN_NOMBRE

    # Actividad: misma actividad escrita distinto -> una sola
    df["actividad_clave"] = df["actividad_original"].map(lambda x: clave(x) if pd.notna(x) else pd.NA)
    variantes = df.groupby("actividad_clave")["actividad_original"].nunique()
    unificadas = int((variantes > 1).sum())
    # Se muestra la forma más común en que se escribió cada actividad (conserva tildes)
    mas_comun = df.dropna(subset=["actividad_clave"]).groupby("actividad_clave")["actividad_original"].agg(
        lambda s: s.str.upper().value_counts().index[0])
    df["actividad"] = df["actividad_clave"].map(lambda x: a_oracion(mas_comun[x]) if pd.notna(x) else SIN_DATO)
    bitacora.append(
        f"Actividades normalizadas: {df['actividad_original'].nunique()} textos distintos quedaron en "
        f"{df['actividad'].nunique()} actividades ({plural(unificadas, 'se escribía', 'se escribían')} de más de una forma)."
    )

    # Categoría (rubro)
    df["categoria"] = df["actividad_original"].map(categorizar)
    otros = int((df["categoria"] == OTROS).sum())
    bitacora.append(
        f"Cada actividad se clasificó en una de {len(CATEGORIAS) + 1} categorías. "
        f"{otros} licencias ({otros / max(len(df), 1):.0%}) quedaron en «{OTROS}»."
    )

    # Distrito
    df["distrito"] = df["distrito"].map(nombre_distrito)
    bitacora.append("Distritos con formato legible: «SANTA_ANA» → «Santa Ana».")

    # Fecha
    if "fecha_aprobacion" in df.columns:
        originales = df["fecha_aprobacion"].notna()
        df["fecha_aprobacion"] = a_fecha(df["fecha_aprobacion"])
        invalidas = int((originales & df["fecha_aprobacion"].isna()).sum())
        df["anio"] = df["fecha_aprobacion"].dt.year.astype("Int64")
        nota = f" {plural(invalidas, 'fecha no era válida y quedó vacía', 'fechas no eran válidas y quedaron vacías')}." if invalidas else ""
        bitacora.append("Fechas de aprobación convertidas a fecha real (día/mes/año)." + nota)
    else:
        df["fecha_aprobacion"] = pd.NaT
        df["anio"] = pd.array([pd.NA] * len(df), dtype="Int64")

    # Licencia de licores
    if "patente_licores" in df.columns:
        df["patente_licores"] = df["patente_licores"].str.replace(r"\D", "", regex=True).replace("", pd.NA)
        df["tiene_licores"] = df["patente_licores"].notna()
        bitacora.append(f"{plural(int(df['tiene_licores'].sum()), 'licencia tiene', 'licencias tienen')} además patente de licores.")
    else:
        df["tiene_licores"] = False

    # Tipo de persona (sin exponer nombres)
    if "patentado" in df.columns:
        df["tipo_persona"] = df["patentado"].map(tipo_persona)
        bitacora.append("Se identificó si el patentado es persona física o jurídica (empresa).")
    else:
        df["tipo_persona"] = SIN_DATO

    orden = ["patente", "establecimiento", "actividad", "categoria", "distrito", "fecha_aprobacion", "anio",
             "tiene_licores", "patente_licores", "tipo_persona", "patentado", "direccion", "sector", "mapa",
             "actividad_original"]
    df = df[[c for c in orden if c in df.columns]].reset_index(drop=True)
    return df, bitacora


# ----------------------------------------------------------------------
# 4. Exportación
# ----------------------------------------------------------------------

def a_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8-sig")


def a_excel_bytes(df: pd.DataFrame) -> bytes:
    salida = io.BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl", date_format="YYYY-MM-DD", datetime_format="YYYY-MM-DD") as w:
        df.to_excel(w, index=False, sheet_name="licencias_limpias")
    return salida.getvalue()
