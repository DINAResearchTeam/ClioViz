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


# =============================================================================
# OUTPUTS
# =============================================================================

os.makedirs("./outputs", exist_ok=True)

OUTPUT_ICICLE = r"./outputs/numismatica_icicle.html"
OUTPUT_SIGLOS = r"./outputs/numismatica_siglos.html"
OUTPUT_CUARTOS = r"./outputs/numismatica_cuartos.html"
OUTPUT_MATERIALES = r"./outputs/numismatica_materiales.html"


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset principal...")

# Dataset principal
data = pd.read_excel(PATH_DATASET)

# Dataset numismático
numismatica = pd.read_excel(PATH_COLECCIONES_NUMISMATICAS)

print(numismatica.shape)

# IDs únicos
ids = numismatica["INVENTARIO"].unique()

# =============================================================================
# FILTRADO DEL DATASET
# =============================================================================

"""
Filtrado:
- Museo Arqueológico Nacional
- Objetos presentes en el dataset numismático
"""

df = data[
    (data['DMUSEO'] == ' Museo Arqueológico Nacional ') &
    (data['NINV'].isin(ids))
].reset_index(drop=True)

print("Objetos en el dataframe:", df.shape)

# =============================================================================
# UNIÓN CON DATOS NUMISMÁTICOS
# =============================================================================

df = df.merge(
    numismatica,
    left_on='NINV',
    right_on='INVENTARIO',
    how='left'
)

# Mantener únicamente monedas
df = df[df["OBJE"] == ' Moneda ']


# =============================================================================
# INFORMACIÓN TEMPORAL
# =============================================================================

# Carga de información temporal
tiempo = load_limpiar_tiempo(PATH_TIEMPO)

# Merge temporal
df_num = df.merge(tiempo, on='DATA', how='left')

# Copia de trabajo
df1 = df_num.copy(deep=True)

# =============================================================================
# MATERIALES
# =============================================================================

# Separar materiales múltiples
df1["MATT1"] = df1["MATT"].apply(
    lambda x: str(x).split(";")
    if pd.notnull(x)
    else x
)

# Expandir materiales
df1 = df1.explode("MATT1").reset_index(drop=True)

# =============================================================================
# FILTRADO DE MATERIALES FRECUENTES
# =============================================================================

all_mat = (
    df1
    .groupby("MATT1")
    .size()
    .reset_index(name='counts')
    .sort_values(by='counts', ascending=False)
)

# Mantener materiales con más de 100 registros
all_mat = all_mat[all_mat["counts"] > 100]

df1 = df1[
    df1["MATT1"].isin(
        all_mat["MATT1"].unique().tolist()
    )
].reset_index(drop=True)

# =============================================================================
# CONVERSIÓN DE SIGLOS
# =============================================================================

df1["Siglo"] = df1["Siglo Inicio"].apply(
    lambda x:
        siglo_romano_a_numero(
            x.split(" ")[0],
            es_ac=True if "a.C." in str(x) else False
        )
        if pd.notnull(x)
        else x
)

# =============================================================================
# ETIQUETAS DE SIGLOS
# =============================================================================

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

# Eliminar ".0"
df1["Siglo_EN"] = df1["Siglo_EN"].str.replace(
    ".0",
    "",
    regex=False
)

# =============================================================================
# FILTRADO CRONOLÓGICO
# =============================================================================

total = df1.shape[0]

# Excluir siglos anteriores al VII a.C.
df1 = df1[df1["Siglo"] > -7].reset_index(drop=True)

# Ajuste del eje temporal (sin año 0)
df1["Siglo1"] = df1["Siglo"].apply(
    lambda x: x - 1 if x > 0 else x
)

# =============================================================================
# AGRUPACIÓN FINAL
# =============================================================================

df1 = (
    df1
    .groupby(
        [
            "MATT1",
            "Siglo",
            "Siglo1",
            "Siglo Inicio",
            "Siglo_EN"
        ]
    )
    .size()
    .reset_index(name='counts')
)

# Eliminar valores nulos
df1 = df1[df1["Siglo"].notnull()]

# =============================================================================
# VISUALIZACIÓN
# =============================================================================

fig = go.Figure()

colors = sns.color_palette("colorblind").as_hex()

# =============================================================================
# LÍNEAS POR MATERIAL
# =============================================================================

for i, mat in enumerate(df1["MATT1"].unique().tolist()):

    df_mat = df1[df1["MATT1"] == mat]

    fig.add_trace(
        go.Scatter(
            x=df_mat["Siglo1"],
            y=df_mat["counts"],

            mode='lines',

            name=mat,

            line_shape='spline',

            line=dict(
                color=colors[i % len(colors)],
                width=2
            ),

            hovertemplate=
                'Siglo: %{x} <br>'
                f'Material: {mat}<br>'
                'Cantidad de registros: %{y} '
                '<extra></extra>'
        )
    )

# =============================================================================
# LAYOUT
# =============================================================================

fig.update_layout(
    title=(
        "Evolución temporal de los materiales más "
        "frecuentes en la colección permanente de "
        "numismática del Museo Arqueológico Nacional"
        f"<br><sup>Total de registros: {total}</sup>"
    ),

    xaxis_title='Siglo',

    yaxis_title='Cantidad de piezas',

    template='plotly_white',

    margin=dict(t=100)
)

# Forzar líneas
fig.update_traces(mode='lines')

# =============================================================================
# ETIQUETAS DEL EJE X
# =============================================================================

new_labels = {
    num: [num, siglo]
    for num, siglo in zip(
        df1["Siglo1"].unique().tolist(),
        df1["Siglo Inicio"].unique().tolist()
    )
}

# Ordenar etiquetas
new_labels = dict(sorted(new_labels.items()))

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

# =============================================================================
# LEYENDA
# =============================================================================

fig.update_layout(
    legend_title_text='Material'
)

# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_MATERIALES)