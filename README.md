# 🏪 Tablero de licencias comerciales

Una app web que recibe el archivo de licencias comerciales de un cantón, lo
**limpia**, lo **normaliza** y arma un **tablero interactivo** con las
actividades comerciales.

**Problema que resuelve:** el archivo que publica la municipalidad trae espacios
de más, la misma actividad escrita de varias formas, fechas como texto, nombres
comerciales vacíos y una columna fantasma. Con eso no se puede responder rápido
«¿qué tipo de comercio hay en cada distrito?». Esta app lo hace en segundos.

## Qué hace

| Paso | Ejemplo |
|---|---|
| Lee el archivo y detecta el separador | `\|`, `;`, `,` o tabulador; UTF-8 o latin-1; también Excel |
| Quita la columna fantasma | el `\|` al final de cada línea crea una columna vacía |
| Renombra columnas | `numPatent` → `patente`, `desActivi` → `actividad_original` |
| Limpia el texto | espacios dobles, espacios al final, comillas sobrantes |
| Unifica actividades | `RESTAURANTE`, `restaurante.` y `RESTAURANTE  ` → **Restaurante** |
| Clasifica en 12 categorías | «Venta de repuestos» → **Vehículos y transporte** |
| Arregla distritos y fechas | `SANTA_ANA` → **Santa Ana**; `04/12/2023 00:00:00` → 4 de diciembre de 2023 |
| Detecta licencias de licores | si la columna `numPatLi` tiene número |
| Identifica el tipo de patentado | persona física o jurídica (empresa), sin mostrar nombres |
| Elimina duplicados | filas repetidas al unir reportes |

El tablero tiene filtros por distrito, categoría, año, licencias de licores y
búsqueda de texto, y seis pestañas: **Panorama** (con hallazgos escritos solos),
**Actividades**, **Tendencia**, **Distritos** (mapa de calor), **Datos** (con
descarga en CSV y Excel) y **Limpieza** (la bitácora de todo lo que se hizo).

## El archivo de entrada

Columnas del portal de datos abiertos de la Municipalidad de Santa Ana:
`numPatent`, `desEstabl`, `fecAproba`, `desActivi`, `numPatLi`, `mapa`,
`dirLocCo`, `numSector`, `nomComple`, `nomDistri`.
Las únicas obligatorias son `desActivi` (actividad) y `nomDistri` (distrito).

Fuente de los datos reales: [Portal de Datos Abiertos de la Municipalidad de Santa Ana](https://datosabiertos.santaana.go.cr/dataset/licencias-comerciales-del-canton-afebrero-del-2024).

El archivo `datos_ejemplo_licencias.csv` es **ficticio**: imita el formato y los
problemas del real, pero ningún comercio ni persona existe. Se generó con
`generar_datos_ejemplo.py`.

## Cómo correrla en su computadora

```bash
pip install -r requirements.txt
streamlit run app.py
```

Pruebas automáticas:

```bash
pip install pytest
pytest -v
```

## Cómo publicarla gratis (Streamlit Community Cloud)

### 1. Subir a GitHub (sin terminal)

1. En **github.com**, clic en **New** → nombre: `tablero-licencias` → **Public** → **Create repository**.
2. Clic en **uploading an existing file** y arrastre estos archivos:
   - `app.py`, `limpieza.py`, `graficos.py`
   - `requirements.txt`
   - `datos_ejemplo_licencias.csv`
   - `README.md`, `test_limpieza.py`, `generar_datos_ejemplo.py` (opcionales)
3. Clic en **Commit changes**.

> **Archivos que empiezan con punto** (`.gitignore` y la carpeta `.streamlit`):
> Mac y Windows los esconden, así que a veces no se arrastran. Son opcionales:
> sin `.streamlit/config.toml` la app funciona igual, solo con los colores de
> fábrica. Si los quiere, créelos en GitHub con **Add file → Create new file**
> y escriba el nombre completo (por ejemplo `.streamlit/config.toml`).
> En Mac, `Cmd + Shift + .` muestra los archivos ocultos en el Finder.

### 2. Publicar en Streamlit Community Cloud

1. Entre a **share.streamlit.io** → **Continue with GitHub**.
2. **Create app** → **Yup, I have an app**.
3. Repository: `su-usuario/tablero-licencias` · Branch: `main` · Main file path: `app.py`.
4. App URL (opcional): por ejemplo `licencias-santa-ana.streamlit.app`.
5. **Deploy**. En unos minutos tiene el enlace.

Cada cambio que haga en GitHub se publica solo. Si nadie usa la app en 12
horas, se duerme; cualquier visitante la despierta con un botón.

## ¿Y los datos?

- El archivo que alguien sube se procesa **en memoria** y **no se guarda**.
- El repositorio es público: **no suba ahí archivos reales**. El `.gitignore`
  ya excluye la carpeta `datos_reales/` y los archivos `*_limpio`.
- La pestaña **Datos** esconde el nombre del patentado por defecto, porque puede
  ser una persona física.

## Cómo está organizado

```
app.py                      → la interfaz: carga, filtros, indicadores y pestañas
limpieza.py                 → la lógica: leer, limpiar, normalizar, clasificar (sin Streamlit)
graficos.py                 → los gráficos (Altair)
test_limpieza.py            → 21 pruebas de las reglas de limpieza
generar_datos_ejemplo.py    → crea el archivo de ejemplo ficticio
datos_ejemplo_licencias.csv → 1 512 filas ficticias con problemas típicos
```

## Decisiones que vale la pena conocer

- **El orden de las categorías importa.** «Oficina administrativa de agencia de
  viajes» es Turismo, no Oficinas, porque Turismo se revisa primero. Las reglas
  están en la lista `CATEGORIAS` de `limpieza.py` y se pueden editar.
- **`\bBAR` no es lo mismo que `BAR`.** Sin la marca de inicio de palabra,
  «Barbería» caería en Restaurantes.
- **El último año puede estar incompleto.** Si el archivo llega a febrero, ese
  año sale con una barra más clara y no se usa para comparar.
- **Los colores siguen reglas.** Una sola serie lleva un solo color; el mapa de
  calor usa un solo tono (más oscuro = más licencias).

## Retos para extenderla

1. «Mini super» y «Minisuper», u «Oficina administrativa» y «Oficinas
   administrativas», siguen siendo actividades distintas. Agregue una lista de
   sinónimos para unificarlas.
2. La pestaña Limpieza muestra qué quedó en «Otros». Agregue palabras clave
   para que baje de 2 %.
3. Agregue un filtro por mes y un gráfico de aprobaciones mes a mes.
4. Permita comparar dos archivos (por ejemplo, febrero contra julio) y mostrar
   qué licencias son nuevas.

---

*Python Express II · Profesor Erick Vargas Víctor*
