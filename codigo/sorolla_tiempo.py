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

OUTPUT_SOROLLA = "./outputs/sorolla_barras_tiempo.html"


# =============================================================================
# FUNCIONES
# =============================================================================

def dibujar_arco(punto1, punto2, h):
    """
    Dibuja un arco parabólico entre dos puntos con una altura máxima h.

    :param punto1: Tupla (x1, y1), coordenadas del primer punto.
    :param punto2: Tupla (x2, y2), coordenadas del segundo punto.
    :param h: Altura máxima del arco.
    """

    x1, y1 = punto1
    x2, y2 = punto2

    # Calcular el punto medio
    x_medio = (x1 + x2) / 2

    # Resolver el coeficiente de la parábola
    a = (y1 - h) / (x1 - x_medio) ** 2

    # Generar puntos x para la parábola
    x_vals = np.linspace(x1, x2, 100)
    y_vals = a * (x_vals - x_medio) ** 2 + h

    return x_vals, y_vals


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

df_sorolla = df_sorolla[
    df_sorolla["OBJE"].str.contains("Cuadro", case=False, na=False)
    & (df_sorolla["DATA"].notnull())
]

df_sor1 = df_sorolla.merge(tiempo, on="DATA", how="left")
df_sor1 = df_sor1[df_sor1["DATA"].notnull()]

inicio = 1863
fin = 1923


# =============================================================================
# PROCESAMIENTO DE DATOS
# =============================================================================

#### DATA ####

periodo = df_sor1[df_sor1["Tipo_data"] == "Periodo"]
periodo = (
    periodo.groupby(["Inicio", "Fin"])
    .size()
    .reset_index(name="count")
)

periodo["text"] = (
    "Periodo: " + periodo["Inicio"].astype(str) + " - " + periodo["Fin"].astype(int).astype(str) + "<br>Número de obras: " + periodo["count"].astype(str)
)

periodo["Grupo"] = [
    str(i) + (" obra" if i == 1 else " obras")
    for i in periodo["count"]
]

periodo = periodo[periodo["Inicio"] > inicio]
periodo = periodo[periodo["Fin"] < fin]

periodo1 = periodo[periodo["Fin"] == periodo["Inicio"]]
periodo = periodo[periodo["Fin"] != periodo["Inicio"]]

periodo = periodo.reset_index(drop=True)

unico = df_sor1[df_sor1["Tipo_data"] == "Único"]
unico = pd.concat([unico, periodo1])
unico = unico.reset_index(drop=True)

unico = (
    unico.groupby(["Inicio"])
    .size()
    .reset_index(name="count")
)

aprox = df_sor1[df_sor1["Tipo_data"] == "Aproximación"]

df_apro1 = (
    aprox.groupby(["Inicio"])
    .size()
    .reset_index(name="count")
)

grupos = periodo["Grupo"].unique()


# =============================================================================
# CONFIGURACIÓN DE COLORES
# =============================================================================

palette = sns.color_palette("colorblind", len(grupos))
palette = palette.as_hex()


# =============================================================================
# CREACIÓN DE FIGURA
# =============================================================================

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    shared_yaxes=True,
    vertical_spacing=0.1,
    subplot_titles=(
        (
            f"Datación única ({unico['count'].sum()}) "
            f"y aproximada ({df_apro1['count'].sum()})"
        ),
        f"Datación por periodos ({periodo['count'].sum()})",
    ),
)

fig.update_layout(
    yaxis_title="Número de obras",
    yaxis2_title="Número de obras",
)

fig.update_xaxes(
    range=[inicio, fin],
)


# =============================================================================
# DATACIÓN ÚNICA
# =============================================================================

fig.add_trace(
    go.Scatter(
        x=unico["Inicio"],
        y=unico["count"],
        mode="markers",
        marker=dict(size=10, color=palette[0]),
        showlegend=True,
        name="Única",
        legendgroup="Único",
        text=unico["count"],
        hoverinfo="text",
        hovertemplate=(
            "Año: %{x}<br>"
            "Número de obras: %{y}<extra></extra>"
        ),
    ),
    row=1,
    col=1,
)


# =============================================================================
# DATACIÓN APROXIMADA
# =============================================================================

fig.add_trace(
    go.Scatter(
        x=df_apro1["Inicio"],
        y=df_apro1["count"],
        mode="markers",
        marker=dict(
            size=10,
            color=palette[1],
            symbol="diamond-open",
        ),
        line=dict(width=5),
        showlegend=True,
        name="Aproximada",
        legendgroup="Aproximación",
        text=df_apro1["count"],
        hoverinfo="text",
        hovertemplate=(
            "Año: %{x}<br>"
            "Número de obras: %{y}<extra></extra>"
        ),
    ),
    row=1,
    col=1,
)

for _, i in df_apro1.iterrows():

    fig.add_trace(
        go.Scatter(
            x=[i["Inicio"], i["Inicio"]],
            y=[0, i["count"]],
            mode="lines",
            marker=dict(size=10, color=palette[1]),
            showlegend=False,
            customdata=i[["count"]],
            hoverinfo="none",
            name="Aproximación",
            legendgroup="Aproximación",
            text=i[["count"]],
            hovertemplate=None,
        ),
        row=1,
        col=1,
    )


# =============================================================================
# DATACIÓN POR PERIODOS
# =============================================================================

max_v = max([
    max(unico["count"]),
    max(df_apro1["count"]),
    max(periodo["count"]),
])

palette = sns.color_palette("colorblind", len(grupos))
palette = palette.as_hex()

for g in grupos:

    p1 = periodo[periodo["Grupo"] == g]

    for i in range(len(p1)):

        x1 = p1.iloc[i]["Inicio"]
        x2 = p1.iloc[i]["Fin"]
        altura = p1.iloc[i]["count"]

        grupo = grupos.tolist().index(p1.iloc[i]["Grupo"])
        g = grupos[grupo]

        x, y = dibujar_arco((x1, 0), (x2, 0), altura)

        fig.append_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                legendgroup=p1.iloc[i]["Grupo"],
                line=dict(color=palette[0]),
                name=p1.iloc[i]["Grupo"],
                text=p1.iloc[i]["text"],
                hoverinfo="text",
                showlegend=False,
            ),
            row=2,
            col=1,
        )


# =============================================================================
# LAYOUT FINAL
# =============================================================================

theme = "plotly_white"

fig.update_layout(
    hovermode="x",
    template=theme,
    title=(
        "Producción de cuadros a lo largo de la vida "
        f"de Sorolla ({inicio}-{fin}) por tipo de datación"
    ),
    height=800,
    width=1500,
    yaxis_fixedrange=True,
    yaxis2_fixedrange=True,
    xaxis_showticklabels=True,
    xaxis2_showticklabels=True,
)

fig.update_traces(
    marker=dict(
        line=dict(width=2, color=palette[1])
    ),
    selector=dict(
        mode="markers",
        name="Aproximada",
    ),
)

fig.update_xaxes(
    row=2,
    col=1,
    matches="x",
)

fig.update_yaxes(
    range=[-1, max_v + 1],
    row=1,
    col=1,
)

fig.update_yaxes(
    range=[-1, max_v + 1],
    row=2,
    col=1,
)

# Posición de la leyenda
fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="right",
        x=0.2,
    )
)

# Separación entre grupos de leyenda
fig.update_layout(legend_tracegroupgap=5)


# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_SOROLLA)