"""
generar_datos_ejemplo.py — Crea datos_ejemplo_licencias.csv con datos FICTICIOS.

Imita el formato del archivo de licencias comerciales de la Municipalidad de
Santa Ana (separado por "|", fechas día/mes/año, distrito como SANTA_ANA) y
también sus problemas: espacios de más, puntos al final, mayúsculas
desparejas, nombres comerciales vacíos, duplicados y una que otra fecha mala.

Ningún establecimiento ni patentado es real: los nombres se arman al azar.

    python generar_datos_ejemplo.py
"""

import random
from datetime import date, timedelta

random.seed(2024)

DISTRITOS = {"POZOS": 34, "SANTA_ANA": 28, "URUCA": 13, "BRASIL": 10, "PIEDADES": 9, "SALITRAL": 6}

# (texto de la actividad como lo escribiría alguien en ventanilla, peso)
ACTIVIDADES = [
    ("RESTAURANTE", 60), ("RESTAURANTE.", 8), ("SODA", 30), ("SODA Y CAFETERIA", 10), ("CAFETERIA", 14),
    ("PANADERIA Y REPOSTERIA", 9), ("PIZZERIA", 7), ("BAR Y RESTAURANTE", 9), ("VENTA DE COMIDA RAPIDA", 8),
    ("MINI SUPER", 22), ("MINISUPER", 8), ("SUPERMERCADO", 5), ("PULPERIA", 9), ("VERDULERIA", 6), ("CARNICERIA", 5),
    ("OFICINA ADMINISTRATIVA", 55), ("OFICINA ADMINISTRATIVA.", 12), ("OFICINAS ADMINISTRATIVAS", 9),
    ("CONSULTORIA EN SOFTWARE", 12), ("SERVICIOS PROFESIONALES DE CONTABILIDAD", 8), ("BUFETE DE ABOGADOS Y NOTARIA", 9),
    ("CORREDURIA DE SEGUROS", 5), ("AGENCIA DE PUBLICIDAD", 5), ("OFICINA ADMINISTRATIVA DE AGENCIA DE VIAJES.", 6),
    ("SALON DE BELLEZA", 18), ("SALÓN DE BELLEZA", 5), ("BARBERIA", 12), ("ESTETICA Y SPA", 7), ("GIMNASIO", 6),
    ("CONSULTORIO MEDICO", 14), ("CLINICA DENTAL", 10), ("FARMACIA", 9), ("OPTICA", 4), ("VETERINARIA", 6),
    ("VENTA DE ROPA", 20), ("BOUTIQUE", 9), ("VENTA DE BISUTERIA Y JOYERIA.", 6), ("BAZAR", 8), ("LIBRERIA", 5),
    ("VENTA DE MUEBLES", 5), ("FERRETERIA", 7), ("VENTA DE MATERIALES DE CONSTRUCCION", 4), ("TIENDA DE CONVENIENCIA", 5),
    ("TALLER MECANICO", 10), ("LAVACAR", 6), ("VENTA DE REPUESTOS PARA AUTOMOVILES", 6), ("RENT A CAR", 3),
    ("ALQUILER DE LOCALES COMERCIALES", 12), ("BIENES RAICES", 7), ("BODEGA", 6), ("CONSTRUCTORA", 4),
    ("CENTRO EDUCATIVO", 6), ("ACADEMIA DE IDIOMAS", 4), ("GUARDERIA", 5),
    ("HOTEL", 3), ("AIRBNB / ALQUILER DE HABITACIONES", 6), ("AGENCIA DE VIAJES", 4),
    ("FABRICA DE ALIMENTOS", 3), ("IMPRENTA", 3),
    ("CENTRO DE EVENTOS", 3), ("LAVANDERIA", 4), ("VIVERO", 3), ("CERRAJERIA", 2),
]

NOMBRES_A = ["La Esquina", "El Roble", "Don Toño", "Sabor Tico", "Las Palmas", "El Trapiche", "Montaña Azul",
             "Lindora", "El Encuentro", "Mi Tierra", "Los Cerros", "La Cosecha", "El Faro", "Río Oro", "Piedra Blanca",
             "La Fuente", "El Mirador", "Buena Vista", "Valle Verde", "Brisas del Oeste", "Santa Lucía", "Cielo Claro"]
NOMBRES_B = ["", " Express", " Plus", " Center", " & Co", " CR", " Oeste", " 2000"]
CALLES = ["CENTRO COMERCIAL LOS ALMENDROS, LOCAL # {n}", "PLAZA EL ROBLE, LOCAL # {n}",
          "DE LA IGLESIA, {n}0 MTS. AL NORTE", "CONDOMINIO VALLE VERDE, FILIAL # {n}",
          "CALLE {n}, AVENIDA 2", "RUTA NACIONAL 121, {n}5 MTS. SUR-ESTE"]
FORMAS = ["SOCIEDAD ANONIMA", "SOCIEDAD DE RESPONSABILIDAD LIMITADA", "LIMITADA",
          "EMPRESA INDIVIDUAL DE RESPONSABILIDAD LIMITADA"]


def fecha_aleatoria():
    # Más licencias recientes que antiguas, hasta febrero de 2024
    anio = min(2024, int(1996 + (random.random() ** 0.6) * 29))
    inicio = date(anio, 1, 1)
    fin = date(2024, 2, 28) if anio == 2024 else date(anio, 12, 31)
    return inicio + timedelta(days=random.randint(0, (fin - inicio).days))


def patentado(i):
    r = random.random()
    if r < 0.45:
        return f"PATENTADO FICTICIO {i:04d}"  # persona física inventada
    if r < 0.65:
        return f"3-10{random.choice([1, 2])}-{random.randint(100000, 999999)} {random.choice(FORMAS)}   "
    return f"INVERSIONES {random.choice(NOMBRES_A).upper()} {random.choice(FORMAS)}   "


def generar(n=1500):
    textos = [a for a, _ in ACTIVIDADES]
    pesos = [p for _, p in ACTIVIDADES]
    filas = []
    for i in range(n):
        actividad = random.choices(textos, pesos)[0]
        if random.random() < 0.05:
            actividad = actividad.lower()
        if random.random() < 0.05:
            actividad = actividad.replace(" ", "  ", 1)
        distrito = random.choices(list(DISTRITOS), list(DISTRITOS.values()))[0]
        sector = {"POZOS": 328, "SANTA_ANA": 130, "URUCA": 210, "BRASIL": 410, "PIEDADES": 505, "SALITRAL": 612}[distrito]
        nombre = "" if random.random() < 0.06 else (random.choice(NOMBRES_A) + random.choice(NOMBRES_B)).upper()
        if nombre and random.random() < 0.04:
            nombre = f'"{nombre}"'
        con_licores = any(k in actividad.upper() for k in ("RESTAURANTE", "BAR", "MINI", "SUPER", "PULPERIA")) and random.random() < 0.45
        f = fecha_aleatoria()
        fecha = f.strftime("%d/%m/%Y 00:00:00") if random.random() > 0.004 else "31/02/2019 00:00:00"
        filas.append([
            str(1000 + i), nombre, fecha, actividad, str(random.randint(100, 7999)) if con_licores else "",
            f"{sector}{random.randint(100000, 999999)}", CALLES[random.randrange(len(CALLES))].format(n=random.randint(1, 40)) + " ",
            str(sector), patentado(i), distrito,
        ])
    filas += random.sample(filas, 12)  # duplicados exactos, como pasa al unir reportes
    random.shuffle(filas)
    encabezado = "numPatent|desEstabl|fecAproba|desActivi|numPatLi|mapa|dirLocCo|numSector|nomComple|nomDistri|"
    with open("datos_ejemplo_licencias.csv", "w", encoding="utf-8") as f:
        f.write(encabezado + "\n")
        for fila in filas:
            f.write("|".join(fila) + "|\n")
    print(f"datos_ejemplo_licencias.csv: {len(filas)} filas ficticias")


if __name__ == "__main__":
    generar()
