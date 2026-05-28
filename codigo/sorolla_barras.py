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

OUTPUT_BARRAS = "./outputs/sorolla_barras.html"


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset principal...")

data = pd.read_excel(PATH_DATASET)

names = ["Sorolla, Joaquín", "Sorolla Bastida, Joaquín", "SOROLLA BASTIDA, Joaquín", "Sorolla y Bastida, Joaquín"]
# df_sorolla = df[df["AUTT"].str.contains('|'.join(names),case=False,na=False)]
               #  .any(level=0)]
# df_sorolla.shape
df_sorolla = data[data["AUTT"].str.contains('|'.join(names),case=False,na=False)]
# df_sorolla = df[df["AUTT"].str.contains('|'.join(names),case=False,na=False)]

df_icot = df_sorolla.copy(deep=True)
df_icot = df_icot[df_icot['ICOT'].notnull()]
# df_icot["ICOT"] = [i.replace("_x000D_", "").replace(".:", "").replace(":", "") for i in df_icot["ICOT"]]
df_icot["ICOT1"] = df_icot["ICOT"].str.split(' _x000D_')
df_icot = df_icot.explode('ICOT1').reset_index()
df_icot["ICOT1"] = [re.sub("\s+", " ", i.strip()) for i in df_icot["ICOT1"]]

df_icot["ICOT1"] = df_icot["ICOT1"].str.split(' ; ')
df_icot = df_icot.explode('ICOT1').reset_index()
df_icot["ICOT1"] = [i.strip() for i in df_icot["ICOT1"]]

df_icot["ICOT1"] = [re.sub(r'Anverso y reversos|Anverso y reverso|Anverso \.|Anverso|Reverso|En el anverso', '', str(i)) for i in df_icot["ICOT1"]]
df_icot["ICOT1"] = [re.sub(r' \d+|\. Zona derecha|\. Zona izquierda', '', str(i)) for i in df_icot["ICOT1"]]
# remove :
df_icot["ICOT1"] = [re.sub(r":|;", "", str(i)) for i in df_icot["ICOT1"]]
df_icot["ICOT1"] = [re.sub(r" \[.*\]", "", str(i)) for i in df_icot["ICOT1"]]
df_icot["ICOT1"] = [re.sub(r"^\.|_x000D_", "", str(i)) for i in df_icot["ICOT1"]]
df_icot["ICOT1"] = [i.strip() for i in df_icot["ICOT1"]]

df_icot.groupby('ICOT1').size().sort_values(ascending=False).reset_index().rename(columns={0:"count"})

df1 = df_icot.groupby('ICOT1').size().sort_values(ascending=False).reset_index().rename(columns={0:"count", "ICOT1":"ICOT"})
df1["Percentage"] = df1["count"] / df_sorolla.shape[0] * 100
df1 = df1[~df1["ICOT"].str.contains("\[", na=True, case=True)]
df1

fig = go.Figure(frames=[])

# df2 = df1.iloc[0:20, :]
df2 = df1[df1["Percentage"] >=1 ] # se cogen las que tienen un porcentaje mayor o igual al 1%
fig.add_trace(
    go.Bar(
        y=df2['ICOT'], x=df2['count'], orientation='h',
        customdata=df2[['Percentage']],
        hovertemplate='Iconografía: %{y} <br>Número de objetos: %{x} <br>Porcentaje: %{customdata:.2f}% <extra></extra>'
        ))
# reverse the y-axis
fig.update_yaxes(categoryorder='total ascending')
# fig.update_layout(title_text='Términos más empleados en las obras de Sorolla en el campo iconografía de CER.es')
fig.update_layout(title_text='Términos empleados que superan el 1% de aparición dentro del campo iconografía de CER.es <br> con autoría de Sorolla')
fig.update_xaxes(title_text='Número de objetos')
fig.update_yaxes(title_text='Iconografía')
#layout size
# fig.update_layout(width=1000, height=800)
# space between bars
fig.update_layout(bargap=0.3)
# space between bars and text (y-axis)
fig.update_layout(margin=dict(pad=10))
# theme
fig.update_layout(template='plotly_white', autosize=True, margin=dict(t=70, b=50, l=50, r=50),
                  font=dict(size=10))
# color
fig.update_traces(marker_color='#0173b2')


fig.write_html(OUTPUT_BARRAS)