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
from plotly.subplots import make_subplots

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

OUTPUT_SOROLLA_BARRAS = "./outputs/sorolla_barras_soporte.html"


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset principal...")

data = pd.read_excel(PATH_DATASET)

# =============================================================================
# FILTRADO DE OBRAS DE SOROLLA
# =============================================================================

# Variantes posibles del nombre del autor
names = [
    "Sorolla, Joaquín",
    "Sorolla Bastida, Joaquín",
    "SOROLLA BASTIDA, Joaquín",
    "Sorolla y Bastida, Joaquín"
]

# Filtrado de registros relacionados con Sorolla
df_sorolla = data[
    data["AUTT"].str.contains('|'.join(names), case=False, na=False)
]

# =============================================================================
# LIMPIEZA DEL CAMPO ICONOGRÁFICO (ICOT)
# =============================================================================

df_icot = df_sorolla.copy(deep=True)

# Mantener únicamente registros con información iconográfica
df_icot = df_icot[df_icot['ICOT'].notnull()]

# -------------------------------------------------------------------------
# SEPARACIÓN Y NORMALIZACIÓN DEL TEXTO
# -------------------------------------------------------------------------

# Separación por saltos de línea codificados
df_icot["ICOT1"] = df_icot["ICOT"].str.split(' _x000D_')
df_icot = df_icot.explode('ICOT1').reset_index(drop=True)

# Limpieza de espacios
df_icot["ICOT1"] = [
    re.sub(r"\s+", " ", i.strip())
    for i in df_icot["ICOT1"]
]

# Separación por delimitador ";"
df_icot["ICOT1"] = df_icot["ICOT1"].str.split(' ; ')
df_icot = df_icot.explode('ICOT1').reset_index(drop=True)

# Limpieza final de espacios
df_icot["ICOT1"] = [i.strip() for i in df_icot["ICOT1"]]

# -------------------------------------------------------------------------
# LIMPIEZA DE TEXTO
# -------------------------------------------------------------------------

# Eliminación de términos redundantes
df_icot["ICOT1"] = [
    re.sub(
        r'Anverso y reversos|Anverso y reverso|Anverso \.|Anverso|Reverso|En el anverso',
        '',
        str(i)
    )
    for i in df_icot["ICOT1"]
]

# Eliminación de numeraciones y zonas
df_icot["ICOT1"] = [
    re.sub(
        r' \d+|\. Zona derecha|\. Zona izquierda',
        '',
        str(i)
    )
    for i in df_icot["ICOT1"]
]

# Eliminación de signos de puntuación
df_icot["ICOT1"] = [
    re.sub(r":|;", "", str(i))
    for i in df_icot["ICOT1"]
]

# Eliminación de contenido entre corchetes
df_icot["ICOT1"] = [
    re.sub(r" \[.*\]", "", str(i))
    for i in df_icot["ICOT1"]
]

# Eliminación de caracteres residuales
df_icot["ICOT1"] = [
    re.sub(r"^\.|_x000D_", "", str(i))
    for i in df_icot["ICOT1"]
]

# Limpieza final
df_icot["ICOT1"] = [i.strip() for i in df_icot["ICOT1"]]

# =============================================================================
# AGRUPACIÓN Y FRECUENCIAS
# =============================================================================

df1 = (
    df_icot
    .groupby('ICOT1')
    .size()
    .sort_values(ascending=False)
    .reset_index()
    .rename(columns={
        0: "count",
        "ICOT1": "ICOT"
    })
)

# Porcentaje respecto al total de obras de Sorolla
df1["Percentage"] = (
    df1["count"] / df_sorolla.shape[0] * 100
)

# Eliminar registros con corchetes
df1 = df1[
    ~df1["ICOT"].str.contains(r"\[", na=True, case=True)
]

# Mantener categorías con al menos 1%
df_ic1 = df1[df1["Percentage"] >= 1]

# =============================================================================
# AGRUPACIÓN TEMÁTICA
# =============================================================================

grupos = [
    "Representación figura humana",
    "Vida urbana",
    "Costumbrismo social",
    "Representación animal",
    "Representación de paisajes"
]

df_ic1.loc[:, "Grupos"] = [

    # -------------------------------------------------------------
    # FIGURA HUMANA
    # -------------------------------------------------------------
    grupos[0]
    if (
        "Figura femenina" in rep
        or "Figura masculina" in rep
        or "Retrato femenino" in rep
        or "Retrato de la familia Sorolla" in rep
        or "Retrato masculino" in rep
        or "Figura infantil" in rep
        or "Retrato infantil" in rep
        or "Desnudo infantil" in rep
        or "Anatomía" in rep
    )

    # -------------------------------------------------------------
    # VIDA URBANA
    # -------------------------------------------------------------
    else grupos[1]
    if (
        "Vida urbana" in rep
        or "Ocio" in rep
        or "Café" in rep
        or "Mundo del trabajo" in rep
        or "Café-teatro" in rep
    )

    # -------------------------------------------------------------
    # COSTUMBRISMO SOCIAL
    # -------------------------------------------------------------
    else grupos[2]
    if (
        "Costumbrismo social" in rep
        or "Pescador" in rep
        or "Andaluces" in rep
        or "Tipos populares" in rep
        or "Indumentaria popular" in rep
        or "Procesión" in rep
        or "Baile" in rep
        or "Indumentaria" in rep
        or "Hispanic Society of America" in rep
        or "Cataluña. El pescado" in rep
        or "Castilla. La fiesta del pan" in rep
        or "Elaboración de la pasa" in rep
    )

    # -------------------------------------------------------------
    # REPRESENTACIÓN ANIMAL
    # -------------------------------------------------------------
    else grupos[3]
    if (
        "Buey" in rep
        or "Caballo" in rep
    )

    # -------------------------------------------------------------
    # PAISAJES
    # -------------------------------------------------------------
    else grupos[4]
    if (
        "Playa" in rep
        or "Barca" in rep
        or "Paisaje marítimo" in rep
        or "Paisaje" in rep
        or "Paisaje rural" in rep
        or "Elemento arquitectónico" in rep
        or "Interior" in rep
        or "Paisaje urbano"
        or "Baño" in rep
        or "Paisaje de montaña" in rep
    )

    # -------------------------------------------------------------
    # OTROS
    # -------------------------------------------------------------
    else "Otros"

    for rep in df_ic1["ICOT"]
]

# =============================================================================
# PREPARACIÓN DE ETIQUETAS
# =============================================================================

df_ic1["label1"] = [
    i.replace(" ", "<br>")
    for i in df_ic1["ICOT"]
]

df_ic1["text1"] = (
    df_ic1["Grupos"]
    + " - "
    + df_ic1["count"]
        .groupby(df_ic1["Grupos"])
        .transform('sum')
        .astype(str)
)

# =============================================================================
# PREPARACIÓN DE DATOS PARA COMPARACIÓN
# =============================================================================

df_ic2 = df_ic1.copy(deep=True)

# Mantener únicamente ciertos grupos
df_ic2 = df_ic2[
    df_ic2["Grupos"].str.contains(
        "|".join([
            "Costumbrismo social",
            "Representación figura humana",
            "Representación de paisajes",
            "Vida urbana"
        ])
    )
].reset_index(drop=True)

# Eliminar columnas auxiliares
df_ic2 = df_ic2.drop(
    columns=["label1", "text1", "count", "Percentage"]
)

# Merge con dataframe original
df_ic2 = df_icot.merge(
    df_ic2,
    left_on="ICOT1",
    right_on="ICOT",
    how="inner"
)

# =============================================================================
# CONFIGURACIÓN DE SUBPLOTS
# =============================================================================

fig = make_subplots(
    rows=2,
    cols=4,
    horizontal_spacing=0.15,
    vertical_spacing=0.20,
    row_heights=[0.7, 0.7]
)

# Orden de grupos
df_ic2["Grupos"] = pd.Categorical(
    df_ic2["Grupos"],
    categories=[
        "Representación figura humana",
        "Costumbrismo social",
        "Vida urbana",
        "Representación de paisajes"
    ],
    ordered=True
)

colors = sns.color_palette("colorblind").as_hex()

# =============================================================================
# FUNCIÓN DE COMPARACIÓN
# =============================================================================

def comparacion1(df, fig, type, numa, col):

    """
    Añade gráficos de barras horizontales al subplot.

    Parameters
    ----------
    df : pd.DataFrame
        Datos agregados.

    fig : plotly.graph_objects.Figure
        Figura de Plotly.

    type : str
        Tipo de visualización:
        - "count"
        - "Percentage"

    numa : int
        Fila del subplot.

    col : int
        Columna del subplot.

    Returns
    -------
    plotly.graph_objects.Figure
    """

    df["count"] = df["count"].astype(int)

    # Totales por categoría iconográfica
    df["Total"] = (
        df.groupby("ICOT1")["count"]
        .transform('sum')
        .astype(int)
    )

    # Porcentajes
    df["Percentage"] = df["count"] / df["Total"]

    df["Percentage1"] = (
        (df["Percentage"] * 100)
        .round(2)
        .astype(str)
        + "%"
    )

    # Limpieza de etiquetas
    df["Tipo"] = [i.strip() for i in df["Tipo"]]

    # Ordenación
    df = df.sort_values(by="Total", ascending=True)

    order = (
        df.groupby("ICOT1")["count"]
        .sum()
        .sort_values(ascending=True)
        .index
    )

    # Orden de categorías
    df["Tipo"] = pd.Categorical(
        df["Tipo"],
        categories=df["Tipo"].unique(),
        ordered=True
    )

    # ---------------------------------------------------------------------
    # CREACIÓN DE TRAZAS
    # ---------------------------------------------------------------------

    for num, tipo_objeto in enumerate(sorted(df["Tipo"].unique())):

        aux1 = df[df["Tipo"] == tipo_objeto]

        # -------------------------------------------------------------
        # VALORES ABSOLUTOS
        # -------------------------------------------------------------
        if type == "count":

            fig.add_trace(

                go.Bar(
                    y=aux1['ICOT1'],
                    x=aux1['count'],
                    name=tipo_objeto,
                    orientation='h',
                    marker_color=colors[num],
                    legendgroup=tipo_objeto,
                    customdata=aux1[['Tipo']],
                    hovertemplate=(
                        'Iconografía: %{y} <br>'
                        'Tipo de objeto: %{customdata[0]} <br>'
                        'Cantidad: %{x} <extra></extra>'
                    )
                ),

                row=numa,
                col=col
            )

            fig.update_yaxes(
                categoryorder='array',
                categoryarray=order,
                row=numa,
                col=col
            )

        # -------------------------------------------------------------
        # PORCENTAJES
        # -------------------------------------------------------------
        else:

            fig.add_trace(

                go.Bar(
                    y=aux1['ICOT1'],
                    x=aux1['Percentage'],
                    name=tipo_objeto,
                    orientation='h',
                    marker_color=colors[num],
                    customdata=aux1[['Tipo', "Percentage1"]],
                    hovertemplate=(
                        'Iconografía: %{y} <br>'
                        'Tipo de objeto: %{customdata[0]} <br>'
                        'Porcentaje: %{customdata[1]} <extra></extra>'
                    ),
                    legendgroup=tipo_objeto,
                ),

                row=numa,
                col=col
            )

            fig.update_yaxes(
                categoryorder='array',
                categoryarray=order,
                row=numa,
                col=col
            )

    # Ajustes generales
    fig.update_layout(bargap=0.3)
    fig.update_layout(margin_pad=15)

    return fig


# =============================================================================
# GENERACIÓN DE SUBPLOTS
# =============================================================================

for num, grupo in enumerate(
    df_ic2.sort_values(by="Grupos")["Grupos"].unique()
):

    aux = df_ic2[
        df_ic2["Grupos"] == grupo
    ].reset_index(drop=True)

    # Agrupación por iconografía y tipo de objeto
    aux = (
        aux
        .groupby(["ICOT1", "OBJE"])
        .size()
        .reset_index()
        .rename(columns={0: "count"})
    )

    aux.rename(columns={"OBJE": "Tipo"}, inplace=True)

    # -------------------------------------------------------------
    # VALORES ABSOLUTOS Y PORCENTAJES
    # -------------------------------------------------------------
    for n, t in enumerate(["count", "Percentage"]):

        comparacion1(
            aux,
            fig,
            t,
            n + 1,
            num + 1
        )

# =============================================================================
# CONFIGURACIÓN DE EJES
# =============================================================================

# Formato porcentaje
fig.update_layout(
    xaxis5_tickformat=".0%",
    xaxis6_tickformat=".0%",
    xaxis7_tickformat=".0%",
    xaxis8_tickformat=".0%"
)

# Títulos eje Y
fig.update_layout(
    yaxis_title_text='Número absoluto de objetos\n',
    yaxis_title_standoff=20,
)

fig.update_layout(
    yaxis5_title_text='Porcentaje de objetos\n',
    yaxis5_title_standoff=20,
)

# =============================================================================
# ANOTACIONES SUPERIORES
# =============================================================================

x_val = []

for num, grupo in enumerate(
    df_ic2.sort_values(by="Grupos")["Grupos"].unique()
):

    if num == 0:
        x = 0

    elif num == 1:
        x = (1 / 4) + 0.05

    else:
        x = x_val[-1] + (1 / 4) + 0.05

    x_val.append(x)

    fig.add_annotation(
        text=grupo,
        xref="paper",
        yref="paper",
        xanchor="center",
        yanchor="middle",
        x=x,
        y=(.5 - .02),
        align="center",
        showarrow=False,
        font=dict(size=16)
    )

# =============================================================================
# TEMA Y CONFIGURACIÓN GENERAL
# =============================================================================

fig.update_layout(
    template='plotly_white',
    legend={'traceorder': 'reversed'},
    yaxis_fixedrange=True,
    yaxis2_fixedrange=True,
    yaxis3_fixedrange=True,
    yaxis4_fixedrange=True,
    yaxis5_fixedrange=True,
    yaxis6_fixedrange=True,
)

# Compartir ejes X
fig.update_xaxes(row=1, col=2, matches='x')
fig.update_xaxes(row=1, col=3, matches='x')
fig.update_xaxes(row=1, col=4, matches='x')

fig.update_xaxes(row=2, col=2, matches='x5')
fig.update_xaxes(row=2, col=3, matches='x5')
fig.update_xaxes(row=2, col=4, matches='x5')

# =============================================================================
# LAYOUT FINAL
# =============================================================================

fig.update_layout(
    title=(
        'Comparación de las principales iconografías '
        'con autoría de Sorolla según agrupaciones '
        'propias dentro del campo iconografía de CER.es'
    ),
    title_x=0.5,
    margin=dict(t=120, l=250, r=0),
)

# Configuración de leyenda
fig.update_layout(
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5
    )
)

# Mostrar leyenda solo en primeras trazas
for i in range(len(fig.data)):

    if i in range(0, 3):
        fig.data[i].showlegend = True

    else:
        fig.data[i].showlegend = False

# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_SOROLLA_BARRAS)

# Mostrar figura
fig.show()