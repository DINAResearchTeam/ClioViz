# =============================================================================
# IMPORTS
# =============================================================================

import os
import re

import branca.colormap as cm
import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from folium import plugins
from plotly.subplots import make_subplots

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

OUTPUT_SOROLLA_TIEMPO = "./outputs/sorolla_obras.html"

tiempo = load_limpiar_tiempo(PATH_TIEMPO)


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset principal...")

data = pd.read_excel(PATH_DATASET)

# Carga de información temporal
tiempo = load_limpiar_tiempo(PATH_TIEMPO)
tiempo["Inicio"] = pd.to_numeric(tiempo["Inicio"], errors="coerce")
tiempo["Fin"] = pd.to_numeric(tiempo["Fin"], errors="coerce")


# =============================================================================
# FILTRADO DE OBRAS DE SOROLLA
# =============================================================================

# Variantes posibles del nombre del autor
names = [
    "Sorolla, Joaquín",
    "Sorolla Bastida, Joaquín",
    "SOROLLA BASTIDA, Joaquín",
    "Sorolla y Bastida, Joaquín",
]

# Filtrado de registros relacionados con Sorolla
df_sorolla = data[
    data["AUTT"].str.contains("|".join(names), case=False, na=False)
]


df_sorolla["OBJE"] = ["Cuadro" if "Pintura" in i or "Óleo" in i or "Pintura mural" in i else i.strip()
               for i in df_sorolla["OBJE"]]
df_sorolla = df_sorolla[df_sorolla["OBJE"] != "Fotografía"]
df_sorolla = df_sorolla.merge(tiempo, on="DATA", how="left")
df_sorolla = df_sorolla[df_sorolla["DATA"].notnull()]

df_sorolla["range"] = [range(int(row["Inicio"]), int(row["Fin"]) + 1) if row["Tipo_data"] == "Periodo" else
                          [int(row["Inicio"])]
                       for num, row in df_sorolla.iterrows()
                       ]

df_sorolla["range1"] = [range(int(row["Inicio"]), int(row["Fin"]) + 1) if row["Tipo_data"] == "Periodo" else
                       [int(row["Inicio"])] if row["Tipo_data"] == "Único" else
                          range(int(row["Inicio"]) - 5, int(row["Inicio"]) + 6)
                       for num, row in df_sorolla.iterrows()
                       ]
df_sorolla["add"] = df_sorolla.apply(lambda x: 1 if x["Tipo_data"] == 'Único' else 
                                     1/len(x["range1"]), axis=1)
inicio = 1863
fin = 1923

df_fechas = pd.DataFrame(columns=["Fecha", "num", "total"])

for i in range(inicio, fin):
    obj = df_sorolla[df_sorolla["range1"].apply(lambda x: i in x)]
    values = obj["add"].sum()
    df_fechas = pd.concat([df_fechas, pd.DataFrame({"Fecha": [i], "num": [values], 'total': [obj.shape[0]]}, columns=["Fecha", "num", "total"])], axis=0)

df_fechas = df_fechas.reset_index(drop=True)
etapas = {
    'Formación': [1880, 1889],
    'Consolidación': [1890, 1899],
    'Culminación': [1900, 1905],
    # 'Ultimos años': [1911, 1920]
    'Últimos años': [1906, 1920]
}


etapas = {
    'Formación': [1880, 1889],
    'Consolidación': [1890, 1899],
    'Culminación': [1900, 1905],
    # 'Ultimos años': [1911, 1920]
    'Últimos años': [1906, 1920]
}

fig = go.Figure()

colors = sns.color_palette("colorblind").as_hex()

df_fechas["num1"] = df_fechas["num"].apply(lambda x: round(x, 0))

inicio = df_fechas["Fecha"].min()
fin = df_fechas["Fecha"].max()

fig.add_trace(go.Scatter(x=df_fechas["Fecha"], y=df_fechas["num1"], mode='lines', name='lines',
                         fill='tozeroy',
                         customdata=df_fechas["total"],
                         line=dict(color=colors[0], width=2, shape='spline'),
                         hovertemplate='Año: %{x} <br>Agregado de producción de obras: %{y} <extra></extra>'))

fig.update_layout(
    # title=f'Tendencias en la actividad productiva a lo largo de la vida de Joaquín Sorolla ({inicio}-{fin})<br><sup>Total de obras: {df_sorolla.shape[0]}</sup>',
    title = f"Evolución de la obra atribuida a Joaquín Sorolla en CER.es<br><sup>Total de obras: {df_sorolla.shape[0]}</sup>",
                     xaxis_title='Año',
                     template='plotly_white',
                     yaxis_title='Agregado de producción de obras')


for etapa, rango in etapas.items():
    # add lines on vertical
    fig.add_shape(type="line",
                x0=rango[0], y0=0, x1=rango[0], y1=900,
                line=dict(color="black", width=1, dash="dot")
                )
    # add lines on horizontal
    fig.add_shape(type="line",
                x0=rango[0], y0=900, x1=rango[1]+1, y1=900,
                line=dict(color="black", width=1, dash="dot")
                )
    if etapa == 'Últimos años':
        fig.add_shape(type="line",
                x0=rango[1]+1, y0=0, x1=rango[1]+1, y1=900,
                line=dict(color="black", width=1, dash="dot")
                )

    # add text
    fig.add_annotation(x=rango[0]+2, y=900, text=etapa, showarrow=False, yshift=10)

fig.update_xaxes(range=[1877, fin], showgrid=False)

# save html

fig.write_html(OUTPUT_SOROLLA_TIEMPO)
