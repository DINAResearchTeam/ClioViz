# =============================================================================
# IMPORTS
# =============================================================================

import os
import re

import numpy as np
import pandas as pd
import geopandas as gpd

import folium
from folium import plugins

import plotly.graph_objects as go
import seaborn as sns

import branca.colormap as cm

from utils import *

# =============================================================================
# RUTAS DE ARCHIVOS
# =============================================================================

PATH_DATASET = r"../datos/FMUS.xlsx"
PATH_TIEMPO = r"../datos/creados/tiempo_nuevo4.xlsx"
PATH_PROVINCIAS = r"../datos/creados/provincias.geojson"
PATH_MUSEOS = r"../datos/creados/museos_prov1.csv"
PATH_COLECCIONES_NUMISMATICAS = (
    r"../datos/colecciones/2.CLIOVIZ_26082024_Numismática.xlsx"
)

# -------------------------------------------------------------------------
# CREACIÓN DE DIRECTORIO DE SALIDA
# -------------------------------------------------------------------------

if not os.path.exists("./outputs"):
    os.makedirs("./outputs")

# -------------------------------------------------------------------------
# ARCHIVOS DE SALIDA
# -------------------------------------------------------------------------

OUTPUT_ICICLE = r"./outputs/numismatica_icicle.html"
OUTPUT_SIGLOS = r"./outputs/numismatica_siglos.html"
OUTPUT_CUARTOS = r"./outputs/numismatica_cuartos.html"
OUTPUT_MATERIALES = r"./outputs/numismatica_materiales.html"


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset principal...")

# -------------------------------------------------------------------------
# CARGA DEL DATASET GENERAL
# -------------------------------------------------------------------------

data = pd.read_excel(PATH_DATASET)

# -------------------------------------------------------------------------
# CARGA DEL DATASET NUMISMÁTICO
# -------------------------------------------------------------------------

numismatica = pd.read_excel(PATH_COLECCIONES_NUMISMATICAS)

print(numismatica.shape)

# IDs únicos de inventario presentes en el dataset numismático
ids = numismatica["INVENTARIO"].unique()

# -------------------------------------------------------------------------
# FILTRADO DEL DATASET PRINCIPAL
# -------------------------------------------------------------------------

"""
Se filtran únicamente:
- Registros pertenecientes al Museo Arqueológico Nacional.
- Registros cuyo número de inventario esté incluido
  en el dataset numismático.
"""

df = data[
    (data['DMUSEO'] == ' Museo Arqueológico Nacional ') &
    (data['NINV'].isin(ids))
].reset_index(drop=True)

print("Objetos en el dataframe:", df.shape)

# -------------------------------------------------------------------------
# UNIÓN CON INFORMACIÓN NUMISMÁTICA
# -------------------------------------------------------------------------

df = df.merge(
    numismatica,
    left_on='NINV',
    right_on='INVENTARIO',
    how='left'
)

# -------------------------------------------------------------------------
# FILTRADO DE OBJETOS
# -------------------------------------------------------------------------

# Se conservan únicamente objetos clasificados como moneda
df = df[df["OBJE"] == ' Moneda ']


# =============================================================================
# CARGA Y PREPARACIÓN DE INFORMACIÓN TEMPORAL
# =============================================================================

# Carga y limpieza de información cronológica
tiempo = load_limpiar_tiempo(PATH_TIEMPO)

# Unión con datos cronológicos
df_num = df.merge(tiempo, on='DATA', how='left')

# Copia de trabajo
df1 = df_num.copy(deep=True)

# -------------------------------------------------------------------------
# FILTRADO DE REGISTROS CON FECHAS
# -------------------------------------------------------------------------

df1 = df1[df1["Inicio"].notnull()]

# Conversión de tipos
df1["Inicio"] = df1["Inicio"].astype(int)
df1["Fin"] = df1["Fin"].astype(float)

# -------------------------------------------------------------------------
# INFORMACIÓN GENERAL
# -------------------------------------------------------------------------

total = df1.shape[0]

print(f"Total registros con fecha: {total}")
print(total / df_num.shape[0] * 100)


# =============================================================================
# GENERACIÓN DE RANGOS TEMPORALES
# =============================================================================

"""
Se generan dos tipos de rangos:

range1:
    Incluye el año final del periodo.

range2:
    Excluye el año final del periodo.

Casos:
------
- Periodo:
    Se genera un rango de años.
- Único:
    Se utiliza únicamente el año concreto.
- Aproximado:
    Se genera un rango ±5 años.
"""

# -------------------------------------------------------------------------
# RANGE 1
# -------------------------------------------------------------------------

df1["range1"] = [
    range(int(row["Inicio"]), int(row["Fin"]) + 1)
    if row["Tipo_data"] == "Periodo"
    else [int(row["Inicio"])]
    if row["Tipo_data"] == "Único"
    else range(int(row["Inicio"]) - 5, int(row["Inicio"]) + 6)
    for _, row in df1.iterrows()
]

# -------------------------------------------------------------------------
# RANGE 2
# -------------------------------------------------------------------------

df1["range2"] = [
    range(int(row["Inicio"]), int(row["Fin"]))
    if row["Tipo_data"] == "Periodo"
    else [int(row["Inicio"])]
    if row["Tipo_data"] == "Único"
    else range(int(row["Inicio"]) - 5, int(row["Inicio"]) + 6)
    for _, row in df1.iterrows()
]


# =============================================================================
# PESOS DE DISTRIBUCIÓN TEMPORAL
# =============================================================================

"""
Para los registros con periodos amplios:
- El peso se distribuye proporcionalmente
  entre todos los años del rango.
"""

# Peso principal
df1["add"] = df1.apply(
    lambda x:
        1
        if x["Tipo_data"] == 'Único'
        else 1 / len(x["range1"]),
    axis=1
)

# Peso alternativo
df1["add2"] = df1.apply(
    lambda x:
        1
        if x["Tipo_data"] == 'Único'
        else 1 / len(x["range2"])
        if len(x["range2"]) > 0
        else 1,
    axis=1
)


# =============================================================================
# DISTRIBUCIÓN CRONOLÓGICA
# =============================================================================

df_fechas = pd.DataFrame(
    columns=["Fecha", "num", "total"]
)

# Año mínimo y máximo
inicio = int(df1["Inicio"].min())
fin = int(df1["Fin"].max()) + 1

# -------------------------------------------------------------------------
# CÁLCULO DE FRECUENCIAS TEMPORALES
# -------------------------------------------------------------------------

for i in range(inicio, fin):

    # Objetos cuyo rango contiene el año i
    obj = df1[df1["range1"].apply(lambda x: i in x)]

    # Suma ponderada
    values = obj["add"].sum()

    # Añadir resultados
    df_fechas = pd.concat(
        [
            df_fechas,
            pd.DataFrame(
                {
                    "Fecha": [i],
                    "num": [values],
                    "total": [obj.shape[0]]
                },
                columns=["Fecha", "num", "total"]
            )
        ],
        axis=0
    )

# Reinicio de índices
df_fechas = df_fechas.reset_index(drop=True)


# =============================================================================
# TRANSFORMACIÓN DE SIGLOS
# =============================================================================

"""
Conversión de siglos romanos a representación numérica.

Ejemplos:
---------
I d.C.   -> 1
II d.C.  -> 2
I a.C.   -> -1
"""

df1["Siglo"] = df1["Siglo Inicio"].apply(
    lambda x:
        siglo_romano_a_numero(
            x.split(" ")[0],
            es_ac=True if "a.C." in str(x) else False
        )
        if pd.notnull(x)
        else x
)

# -------------------------------------------------------------------------
# ETIQUETAS EN INGLÉS
# -------------------------------------------------------------------------

df1["Siglo_EN"] = df1["Siglo"].apply(
    lambda x:
        str(abs(x)) + (
            " BC"
            if x < 0
            else "st"
            if pd.notnull(x) and x == 1
            else "nd"
            if pd.notnull(x) and x == 2
            else "rd"
            if pd.notnull(x) and x == 3
            else "th"
        )
)

df1

# =============================================================================
# AGRUPACIÓN POR SIGLOS
# =============================================================================

# Número total de registros
total = df1.shape[0]

# Agrupación
df1 = (
    df1
    .groupby(["Siglo", "Siglo_EN", "Siglo Inicio"])
    .size()
    .reset_index(name='counts')
)

# Eliminación de valores nulos
df1 = df1[df1["Siglo"].notnull()]

# Filtrado de siglos anteriores al VII a.C.
df1 = df1[df1["Siglo"] > -7]

# -------------------------------------------------------------------------
# AJUSTE DE EJE CRONOLÓGICO
# -------------------------------------------------------------------------

"""
Se elimina el hueco entre:
- Siglos a.C.
- Siglos d.C.

No existe año 0, por lo que se ajusta:
- d.C. -> -1
"""

df1["Siglo1"] = df1["Siglo"].apply(
    lambda x: x - 1 if x > 0 else x
)


# =============================================================================
# VISUALIZACIÓN
# =============================================================================

# Creación de figura
fig = go.Figure()

# -------------------------------------------------------------------------
# GRÁFICA PRINCIPAL
# -------------------------------------------------------------------------

colors = sns.color_palette("colorblind").as_hex()

fig.add_trace(
    go.Scatter(
        x=df1["Siglo1"],
        y=df1["counts"],
        mode='lines',
        name='lines',

        fill='tozeroy',

        line_shape='spline',

        line=dict(
            color=colors[0],
            width=2
        ),

        hovertemplate=(
            'Century: %{x} <br>'
            'Number of records: %{y} '
            '<extra></extra>'
        )
    )
)

# -------------------------------------------------------------------------
# CONFIGURACIÓN DEL LAYOUT
# -------------------------------------------------------------------------

fig.update_layout(
    title=(
        "Evolución cronológica de piezas numismáticas "
        "en la exposición permanente del "
        "Museo Arqueológico Nacional"
        f"<br><sup>Total de registros: {total}</sup>"
    ),

    xaxis_title='Century',
    yaxis_title='Number of pieces',
)

# Forzar visualización como línea
fig.update_traces(mode='lines')


# =============================================================================
# ETIQUETAS DEL EJE X
# =============================================================================

# Diccionario de etiquetas
new_labels = {
    num: [num, siglo]
    for num, siglo in zip(
        df1["Siglo1"].unique().tolist(),
        df1["Siglo_EN"].unique().tolist()
    )
}

# Ordenar por clave
new_labels = dict(sorted(new_labels.items()))

# Actualización de etiquetas del eje X
fig.update_xaxes(
    tickmode='array',

    tickvals=sorted(
        df1["Siglo1"].unique().tolist()
    ),

    ticktext=[
        f"{siglo}"
        for num, siglo in new_labels.values()
    ],

    showgrid=False,

    nticks=5
)

# Plantilla visual
fig.update_layout(template='plotly_white')


# =============================================================================
# EXPORTACIÓN
# =============================================================================

# Guardar visualización
fig.write_html(OUTPUT_SIGLOS)