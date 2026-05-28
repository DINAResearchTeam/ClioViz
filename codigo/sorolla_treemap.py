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

OUTPUT_TREEMAP = "./outputs/sorolla_treemap.html"


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

# Separación inicial por saltos de línea codificados
df_icot["ICOT1"] = df_icot["ICOT"].str.split(' _x000D_')
df_icot = df_icot.explode('ICOT1').reset_index(drop=True)

# Limpieza de espacios
df_icot["ICOT1"] = [
    re.sub(r"\s+", " ", i.strip())
    for i in df_icot["ICOT1"]
]

# Separación por categorías delimitadas por ";"
df_icot["ICOT1"] = df_icot["ICOT1"].str.split(' ; ')
df_icot = df_icot.explode('ICOT1').reset_index(drop=True)

# Eliminación de espacios sobrantes
df_icot["ICOT1"] = [i.strip() for i in df_icot["ICOT1"]]

# -------------------------------------------------------------------------
# LIMPIEZA DE TEXTO
# -------------------------------------------------------------------------

# Eliminación de términos descriptivos redundantes
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
    re.sub(r' \d+|\. Zona derecha|\. Zona izquierda', '', str(i))
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

# Limpieza final de espacios
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
    .rename(columns={0: "count", "ICOT1": "ICOT"})
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
# PREPARACIÓN DEL TREEMAP
# =============================================================================

df1 = df_ic1.copy(deep=True)

# Evitar conflictos entre categoría y subcategoría
df1['subcategoria_mod'] = df1.apply(
    lambda row:
        row['ICOT'] + '_sub'
        if row['ICOT'] == row['Grupos']
        else row['ICOT'],
    axis=1
)

# DataFrame base del treemap
treemap_df = pd.DataFrame(
    columns=['ids', 'labels', 'parents', 'values']
)

# -------------------------------------------------------------------------
# SUBCATEGORÍAS
# -------------------------------------------------------------------------

for _, row in df1.iterrows():

    treemap_df = pd.concat([
        treemap_df,
        pd.DataFrame({
            'ids': row['subcategoria_mod'],
            'labels': row['ICOT'],
            'parents': row['Grupos'],
            'values': row['count']
        }, index=[0])
    ], ignore_index=True)

# =============================================================================
# NODO TOTAL
# =============================================================================

total_values = treemap_df['values'].sum()

treemap_df = pd.concat([
    treemap_df,
    pd.DataFrame({
        'ids': 'total',
        'labels': 'Total de instancias',
        'parents': '',
        'values': df1['count'].sum()
    }, index=[0])
], ignore_index=True)

# Actualizar etiqueta principal
treemap_df.loc[
    treemap_df['parents'] == '',
    'labels'
] = " - ".join([
    "Total de instancias",
    str(total_values)
])

# =============================================================================
# COLORES
# =============================================================================

color_dict = {
    'total': 'white',
    "": "white"
}

colors = sns.color_palette("colorblind").as_hex()

# Colores por grupo principal
for num, grupo in enumerate(df1['Grupos'].unique()):

    total_grupo = (
        df1[df1['Grupos'] == grupo]['count']
        .sum()
    )

    color_dict[grupo] = colors[num]

    treemap_df = pd.concat([
        treemap_df,
        pd.DataFrame({
            'ids': grupo,
            'labels': " - ".join([grupo, str(total_grupo)]),
            'parents': 'total',
            'values': total_grupo,
            'label1': grupo
        }, index=[0])
    ], ignore_index=True)

# =============================================================================
# PORCENTAJES Y HOVER
# =============================================================================

treemap_df["perc"] = (
    treemap_df["values"]
    / treemap_df["values"]
        .groupby(treemap_df["parents"])
        .transform('sum')
    * 100
).astype(float)

treemap_df["perc"] = treemap_df["perc"].round(2)

# -------------------------------------------------------------------------
# TEXTO DEL HOVER
# -------------------------------------------------------------------------

treemap_df['text'] = [

    i['ids']
    if " - " in i["labels"]
    else (
        i['labels']
        + "<br>"
        + "Categoria: "
        + i['parents']
    )

    for _, i in treemap_df.iterrows()
]

treemap_df['text'] = (
    treemap_df['text']
    + '<br>'
    + 'Cantidad: '
    + treemap_df['values'].astype(str)
    + '<br>'
    + 'Porcentaje: '
    + treemap_df['perc'].astype(str)
    + '%'
    + '<extra></extra>'
)

# Eliminar texto del nodo raíz
treemap_df.loc[
    treemap_df['parents'] == '',
    'text'
] = ""

# =============================================================================
# ETIQUETAS Y COLORES
# =============================================================================

# Reemplazar espacios por saltos de línea
treemap_df["label1"] = [
    i.replace(" ", "<br>")
    if not " - " in i
    else i
    for i in treemap_df["labels"]
]

# Asignar colores
treemap_df['colors'] = [

    color_dict[i["ids"]]
    if " - " in i["labels"]
    else color_dict[i["parents"]]

    for _, i in treemap_df.iterrows()
]

# =============================================================================
# VISUALIZACIÓN TREEMAP
# =============================================================================

fig = go.Figure(go.Treemap(
    labels=treemap_df['label1'],
    parents=treemap_df['parents'],
    values=treemap_df['values'],
    ids=treemap_df['ids'],
    hovertemplate=treemap_df['text'],
    branchvalues='total',
    marker=dict(
        colors=treemap_df['colors'],
    ),
    maxdepth=2
))

# =============================================================================
# CONFIGURACIÓN DEL LAYOUT
# =============================================================================

fig.update_layout(
    title=(
        'Agrupación de términos más empleados en las obras '
        'de Sorolla a partir del campo iconografía de CER.es '
        '<br> en todos los soportes'
    ),
    autosize=True,
    margin=dict(t=90, b=50, l=50, r=50),
)

# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_TREEMAP)