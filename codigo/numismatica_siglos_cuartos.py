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

# IDs de inventario
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

# Unión con información numismática
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

# Carga de información cronológica
tiempo = load_limpiar_tiempo(PATH_TIEMPO)

# Merge temporal
df_num = df.merge(tiempo, on='DATA', how='left')

# Copia de trabajo
df1 = df_num.copy(deep=True)

# Mantener registros con fecha
df1 = df1[df1["Inicio"].notnull()]

# Conversión de tipos
df1["Inicio"] = df1["Inicio"].astype(int)
df1["Fin"] = df1["Fin"].astype(float)

# Total de registros
total = df1.shape[0]

# =============================================================================
# RANGOS TEMPORALES
# =============================================================================

"""
Generación de rangos según el tipo de fecha:

- Periodo  -> rango Inicio-Fin
- Único    -> año único
- Aproximado -> ±5 años
"""

df1["range1"] = [
    range(int(row["Inicio"]), int(row["Fin"]) + 1)
    if row["Tipo_data"] == "Periodo"
    else [int(row["Inicio"])]
    if row["Tipo_data"] == "Único"
    else range(int(row["Inicio"]) - 5, int(row["Inicio"]) + 6)

    for _, row in df1.iterrows()
]

# Peso temporal
df1["add2"] = df1.apply(
    lambda x:
        1
        if x["Tipo_data"] == 'Único'
        else 1 / len(x["range1"])
        if len(x["range1"]) > 0
        else 1,
    axis=1
)


# =============================================================================
# CONFIGURACIÓN TEMPORAL
# =============================================================================

# Inicio Edad Media
inicio = 476

# Fecha máxima
fin = int(
    max(
        df1["Fin"].max(),
        df1["Inicio"].max()
    ) + 1
)

# Intervalo temporal
intervalo = 25

# DataFrame auxiliar
df_fechas = pd.DataFrame(columns=["Fecha", "num"])


# =============================================================================
# AGRUPACIÓN TEMPORAL
# =============================================================================

df2 = df1.copy(deep=True)

# Filtrar rango temporal
df2 = df2[
    (df2["Inicio"] >= inicio) &
    (df2["Inicio"] <= fin)
]

total = df2.shape[0]

# Valores posibles
range_values = list(range(inicio, fin, intervalo))

# =============================================================================
# ASIGNACIÓN AL INTERVALO MÁS CERCANO
# =============================================================================

df2['closest'] = df2['Inicio'].apply(
    lambda x: min(
        range_values,
        key=lambda y: abs(y - x)
    )
)

# =============================================================================
# GENERACIÓN DE ETIQUETAS TEMPORALES
# =============================================================================

siglos_df = pd.DataFrame(
    columns=['order', 'siglo_num', 'texto']
)

siglos_df[['order', 'siglo_num', 'texto']] = [
    cuarto_del_siglo(x)
    for x in range(inicio, fin, intervalo)
]

siglos_df['closest'] = range(inicio, fin, intervalo)

# Etiquetas del dataframe principal
df2[['order', 'siglo_num', 'texto']] = (
    df2['closest']
    .apply(lambda x: pd.Series(cuarto_del_siglo(x)))
)

# =============================================================================
# AGRUPACIÓN FINAL
# =============================================================================

df2 = (
    df2
    .groupby(['closest', 'texto'])
    .size()
    .reset_index(name='num')
)

df2 = df2.sort_values(by='closest')

# Añadir intervalos faltantes
df2 = df2.merge(
    siglos_df,
    on=['closest', 'texto'],
    how='right'
)

# Completar valores nulos
df2["num"] = df2["num"].fillna(0)
df2["num"] = df2["num"].astype(int)

# Orden final
df2 = df2.sort_values(by='closest')


# =============================================================================
# VISUALIZACIÓN
# =============================================================================

fig = go.Figure()

colors = sns.color_palette("colorblind").as_hex()

# =============================================================================
# LÍNEA PRINCIPAL
# =============================================================================

fig.add_trace(
    go.Scatter(
        x=df2["texto"],
        y=df2["num"],

        mode='lines',
        name='lines',

        customdata=df2["texto"],

        fill='tozeroy',

        line_shape='spline',

        line=dict(
            color=colors[0],
            width=2
        )
    )
)

# =============================================================================
# ETIQUETAS DEL EJE X
# =============================================================================

"""
Mostrar únicamente:
- Primer cuarto de cada siglo
"""

# Índices de "1/4"
index = df2[
    df2["texto"].str.contains("1/4")
].index.tolist()

# Valores asociados
values = df2[
    df2["texto"].str.contains("1/4")
]["texto"].tolist()

# Extraer siglo
values = [
    re.match(r'.*S\.(.*)', v).group(1).strip()
    for v in values
]

# Configuración del eje X
fig.update_xaxes(
    tickvals=index,
    ticktext=values,
    showgrid=False
)


# =============================================================================
# LAYOUT
# =============================================================================

fig.update_layout(
    title=(
        "Evolución cronológica de piezas numismáticas "
        "en la exposición permanente del "
        "Museo Arqueológico Nacional<br>"
        "a partir de 476 d.C. agrupando "
        "en intervalos de 25 años<br>"
        f"<sup>Total de registros: {total}</sup>"
    ),

    xaxis_title='Siglo',

    yaxis_title='Cantidad de piezas',

    template='plotly_white',

    margin=dict(t=100)
)

# =============================================================================
# HOVER
# =============================================================================

fig.update_traces(
    hovertemplate=(
        'Intervalo: %{customdata} <br>'
        'Cantidad de piezas: %{y} '
        '<extra></extra>'
    )
)

# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_CUARTOS)