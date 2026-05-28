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

data = pd.read_excel(PATH_DATASET)
numismatica = pd.read_excel(PATH_COLECCIONES_NUMISMATICAS)

print(numismatica.shape)

# IDs de inventario
ids = numismatica["INVENTARIO"].unique()

# =============================================================================
# FILTRADO DEL DATASET PRINCIPAL
# =============================================================================

df = data[
    (data['DMUSEO'] == ' Museo Arqueológico Nacional ') &
    (data['NINV'].isin(ids))
].reset_index(drop=True)

df = df.merge(
    numismatica,
    left_on='NINV',
    right_on='INVENTARIO',
    how='left'
)

df = df[df["OBJE"] == ' Moneda '].reset_index(drop=True)

print("Objetos en el dataframe:", df.shape)


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def clean_context_column(df):
    """
    Limpia espacios en columnas de contexto.

    Parameters
    ----------
    df : pd.DataFrame

    Returns
    -------
    pd.DataFrame
    """
    df["PRIMER NIVEL"] = df["PRIMER NIVEL"].apply(
        lambda x: x.strip() if pd.notnull(x) else x
    )
    return df


def build_id(df):
    """
    Construye IDs jerárquicos únicos.
    """

    cols = [
        "PRIMER NIVEL",
        "SEGUNDO NIVEL",
        "TERCER NIVEL",
        "CUARTO NIVEL",
        "QUINTO NIVEL",
        "SEXTO NIVEL"
    ]

    df["id"] = df.apply(
        lambda x: "_".join([str(x[col]) for col in cols]),
        axis=1
    )

    df["id"] = (
        df["id"]
        .str.replace(" ", "_")
        .str.replace("__", "_")
        .str.replace("__", "_")
        .str.replace("__", "_")
        .str.replace("__", "_")
        .str.replace("__", "_")
    )

    return df


def clean_id_part(part):
    """
    Limpia partes de IDs.
    """
    return (
        part
        .replace(' ', '_')
        .replace(',', '')
        .replace('(', '')
        .replace(')', '')
    )


# =============================================================================
# CARGA DE CONTEXTOS
# =============================================================================

todo = clean_context_column(leer_df("contexto"))
errores = clean_context_column(leer_df("errores"))
amb = clean_context_column(leer_df("ambigüedad"))

# =============================================================================
# LIMPIEZA DE REGISTROS
# =============================================================================

todo = todo[~todo["id"].isin(errores["id"].unique())]
todo = todo[~todo["id"].isin(amb["id"].unique())]

todo["tipo"] = "Periodos de etiqueta unívoca"
amb["tipo"] = "Periodos de etiqueta ambigua"

all_cnt = pd.concat([todo, amb], ignore_index=True)
all_cnt = build_id(all_cnt)

# =============================================================================
# TRATAMIENTO ESPECIAL DE AL-ANDALUS
# =============================================================================

mask_al = (
    (todo["TERCER NIVEL"] == "Al-Andalus") &
    (~todo["CNTT"].str.contains("alta|baja|plena", case=False, na=False))
)

al = todo.loc[
    mask_al,
    [
        "CNTT",
        "PRIMER NIVEL",
        "SEGUNDO NIVEL",
        "TERCER NIVEL",
        "CUARTO NIVEL",
        "QUINTO NIVEL",
        "SEXTO NIVEL",
        "id"
    ]
]

todo = todo[~todo["id"].isin(al["id"].unique())]

al2 = al.copy(deep=True)
al2["SEGUNDO NIVEL"] = "Baja Edad Media"

al3 = al.copy(deep=True)
al3["SEGUNDO NIVEL"] = "Plena Edad Media"

amb1 = pd.concat([al, al2, al3], ignore_index=True)
amb1 = build_id(amb1)

# -------------------------------------------------------------------------
# AMBIGUOS
# -------------------------------------------------------------------------

mask_amb = (
    (amb["TERCER NIVEL"] == "Al-Andalus") &
    (~amb["CNTT"].str.contains("alta|baja|plena", case=False, na=False))
)

amb2 = amb.loc[
    mask_amb,
    [
        "CNTT",
        "PRIMER NIVEL",
        "SEGUNDO NIVEL",
        "TERCER NIVEL",
        "CUARTO NIVEL",
        "QUINTO NIVEL",
        "SEXTO NIVEL",
        "id"
    ]
]

amb = amb[~amb["id"].isin(amb2["id"].unique())]

al2 = amb2.copy(deep=True)
al2["SEGUNDO NIVEL"] = "Baja Edad Media"

al3 = amb2.copy(deep=True)
al3["SEGUNDO NIVEL"] = "Plena Edad Media"

amb = pd.concat(
    [amb, amb2, al2, al3, amb1],
    ignore_index=True
)

amb = build_id(amb)
amb["tipo"] = "Periodos de etiqueta ambigua"

# =============================================================================
# DATASET FINAL DE CONTEXTOS
# =============================================================================

all_cnt = pd.concat([todo, amb], ignore_index=True)
all_cnt = build_id(all_cnt)

# =============================================================================
# MÉTRICAS GENERALES
# =============================================================================

man_full = df.copy(deep=True)

ind1 = man_full[(man_full['CNTT'].isin(all_cnt['CNTT']))].index
ind2 = man_full[man_full['CNTT'].notnull()].index

len(ind1.intersection(ind2))

total_reg = df.shape[0]
total_cadenas = man_full["CNTT"].nunique()

print(
    f"Cantidad de registros sin CNTT: "
    f"{man_full[man_full['CNTT'].isna()].shape[0]}"
)

print(
    f"CNTT en df limpiado: "
    f"{man_full[(man_full['CNTT'].isin(all_cnt['CNTT'])) & (man_full['CNTT'].notnull())].shape[0]}"
)

man_full = man_full[man_full["CNTT"].notnull()]

print(f"Cantidad de registros con CNTT: {man_full.shape[0]}")
print(man_full.shape[0] / total_reg * 100)

labels = {
    'total': man_full.shape[0],
}

# =============================================================================
# MERGE CONTEXTOS
# =============================================================================

man_full = man_full.merge(all_cnt, on="CNTT", how="left")

# =============================================================================
# COLORES
# =============================================================================

colors = sns.color_palette("colorblind").as_hex()

primer_label = [
    label.replace(" ", "_")
    for label in man_full['PRIMER NIVEL'].unique().tolist()
    if pd.notnull(label)
]

palette = {
    label: colors[i]
    for i, label in enumerate(primer_label)
}

# =============================================================================
# OBJETOS ÚNICOS
# =============================================================================

man_full["id_obj"] = man_full.apply(
    lambda x: str(x["Idt_Tabla"]) + "_" + str(x["NINV"]),
    axis=1
)

unique_cnt = (
    man_full
    .drop_duplicates(subset=["id_obj"])
    .reset_index(drop=True)
)

labels['excluidos'] = labels['total'] - unique_cnt.shape[0]

etiquetas = (
    unique_cnt
    .groupby(["tipo"])
    .size()
    .reset_index(name='count')
    .sort_values(by='count', ascending=False)
)

labels['unicos'] = (
    etiquetas[etiquetas['tipo'].str.contains("unívoca")]
    ['count']
    .values[0]
)

labels['ambiguos'] = (
    etiquetas[etiquetas['tipo'].str.contains("ambigua")]
    ['count']
    .values[0]
)

# =============================================================================
# ORDEN DE PERIODOS
# =============================================================================

orden_periodos = {
    'Prehistoria': 0,
    'Protohistoria': 1,
    'Edad del Hierro': 1.1,
    'Primer Edad del Hierro': 1.11,
    'Segunda Edad del Hierro': 1.12,
    'Edad Antigua': 2,
    'Cultura Griega': 2.1,
    'Cultura Romana': 2.2,
    'Cultura Cartaginesa': 2.3,
    'Edad Media': 3,
    'Alta Edad Media': 3.1,
    'Plena Edad Media': 3.2,
    'Baja Edad Media': 3.3,
    'Dinastía Qing (China)': 3.4,
    'Edad Moderna': 4,
    'Dinastía de los Austrias': 4.1,
    'Dinastía de Borbón (España)': 4.2,
    'Periodo Edo (Japón)': 4.3,
    'Edad Contemporánea': 5,
    'Sexenio Democrático': 5.1,
    'Segunda República Española': 5.2,
    'Guerra Civil Española': 5.3,
    'Dictadura del General Franco': 5.4,
    'Reino Unido de Gran Bretaña e Irlanda del Norte': 5.5,
    'Periodo Edo (Japón)': 5.6,
    'Dinastía Qing (China)': 5.7,
}


# =============================================================================
# CREACIÓN DE JERARQUÍAS
# =============================================================================

def create_full_df(columns, man_full, flag=None):

    df2 = (
        man_full
        .groupby(columns, dropna=False)
        .size()
        .reset_index(name='count')
    )

    df2 = build_id(df2)

    hierarchy_rows = []
    existing_nodes = set()

    for _, row in df2.iterrows():

        levels = [
            row['PRIMER NIVEL'],
            row['SEGUNDO NIVEL'],
            row['TERCER NIVEL'],
            row['CUARTO NIVEL'],
            row['QUINTO NIVEL'],
            row['SEXTO NIVEL']
        ]

        count = row['count']

        current_parent = ""
        current_id_parts = []

        for level in levels:

            if pd.isna(level):
                continue

            clean_level = clean_id_part(str(level))

            current_id_parts.append(clean_level)

            current_id = '_'.join(current_id_parts)

            if current_id not in existing_nodes:

                hierarchy_rows.append({
                    'ids': current_id,
                    'labels': (
                        level.strip()
                        if isinstance(level, str)
                        else str(level)
                    ),
                    'parents': current_parent,
                    'count': 0
                })

                existing_nodes.add(current_id)

            current_parent = current_id

        if current_parent:

            for node in hierarchy_rows:

                if node['ids'] == current_parent:
                    node['count'] = count
                    break

    # ---------------------------------------------------------------------
    # DATAFRAME FINAL
    # ---------------------------------------------------------------------

    result_df = pd.DataFrame(hierarchy_rows)
    result_df = result_df.sort_values('ids')

    # ---------------------------------------------------------------------
    # CÁLCULO JERÁRQUICO
    # ---------------------------------------------------------------------

    parent_sums = {}

    for _, row in result_df.iterrows():

        parent = row['parents']
        value = row['count']

        while parent:

            if parent in parent_sums:
                parent_sums[parent] += value
            else:
                parent_sums[parent] = value

            parent_row = result_df[result_df['ids'] == parent]

            parent = (
                parent_row['parents'].values[0]
                if not parent_row.empty
                else ''
            )

    result_df['hierarchical_value'] = result_df['count']

    for node_id, sum_value in parent_sums.items():

        result_df.loc[
            result_df['ids'] == node_id,
            'hierarchical_value'
        ] += sum_value

    # ---------------------------------------------------------------------
    # NODO TOTAL
    # ---------------------------------------------------------------------

    total_value = result_df['count'].sum()

    total_row = pd.DataFrame([{
        'ids': 'Total',
        'labels': 'Total de apariciones',
        'parents': '',
        'count': total_value,
        'hierarchical_value': total_value
    }])

    result_df.loc[
        result_df['parents'] == '',
        'parents'
    ] = 'Total'

    result_df = pd.concat(
        [total_row, result_df],
        ignore_index=True
    )

    # ---------------------------------------------------------------------
    # COLORES Y ORDEN
    # ---------------------------------------------------------------------

    result_df['orden'] = (
        result_df['labels']
        .map(orden_periodos)
    )

    result_df["primer_label"] = result_df['ids'].apply(
        lambda x: next(
            (label for label in primer_label if label in x),
            ''
        )
    )

    result_df["color"] = result_df["primer_label"].apply(
        lambda x: palette[x] if x in palette else 'white'
    )

    result_df = result_df.sort_values(
        by=['parents', 'orden'],
        na_position='first'
    )

    # ---------------------------------------------------------------------
    # FLAGS
    # ---------------------------------------------------------------------

    result_df["type"] = flag if flag is not None else np.nan

    return result_df


# =============================================================================
# GENERACIÓN DE DATAFRAMES
# =============================================================================

columns = [
    'PRIMER NIVEL',
    'SEGUNDO NIVEL',
    'TERCER NIVEL',
    'CUARTO NIVEL',
    'QUINTO NIVEL',
    'SEXTO NIVEL',
    'id'
]

df_full = create_full_df(columns, man_full)

# -------------------------------------------------------------------------
# UNÍVOCOS
# -------------------------------------------------------------------------

df_univ = (
    man_full[
        man_full["tipo"] == "Periodos de etiqueta unívoca"
    ]
    .reset_index(drop=True)
)

message_univ = create_full_df(
    columns,
    df_univ,
    flag="univoco"
)

# -------------------------------------------------------------------------
# AMBIGUOS
# -------------------------------------------------------------------------

df_amb = (
    man_full[
        man_full["tipo"] == "Periodos de etiqueta ambigua"
    ]
    .reset_index(drop=True)
)

message_amb = create_full_df(
    columns,
    df_amb,
    flag="ambiguo"
)

# =============================================================================
# MERGE FINAL
# =============================================================================

df_full = df_full.merge(
    message_univ.loc[:, ["ids", "hierarchical_value", "type"]],
    on=["ids"],
    how="left",
    suffixes=("", "_univ")
)

df_full = df_full.merge(
    message_amb.loc[:, ["ids", "hierarchical_value", "type"]],
    on=["ids"],
    how="left",
    suffixes=("", "_amb")
)

df_full["hierarchical_value_univ"] = (
    df_full["hierarchical_value_univ"]
    .apply(lambda x: int(x) if pd.notnull(x) else 0)
)

df_full["hierarchical_value_amb"] = (
    df_full["hierarchical_value_amb"]
    .apply(lambda x: int(x) if pd.notnull(x) else 0)
)

# =============================================================================
# TOOLTIPS
# =============================================================================

df_full["message"] = df_full.apply(
    lambda x:
        f"{x['labels']}<br>"
        f"Quantity: {x['hierarchical_value']:,}<br>"
        f"- Univoque: {x['hierarchical_value_univ']:,}<br>"
        f"- Ambiguous: {x['hierarchical_value_amb']:,}<br>",
    axis=1
)

df_full["message"] = df_full["message"].str.replace("NaN", "0")


# =============================================================================
# ICICLE CHART
# =============================================================================

fig = go.Figure(
    go.Icicle(
        labels=df_full['labels'],
        parents=df_full['parents'],
        ids=df_full['ids'],
        values=df_full['hierarchical_value'],

        marker=dict(
            colors=df_full['color'],
            autocolorscale=False
        ),

        branchvalues='total',

        customdata=df_full['message'],

        hovertemplate='%{customdata}<extra></extra>',

        textinfo='label+value',
        textposition='middle center',
    )
)

# =============================================================================
# LAYOUT
# =============================================================================

fig.update_layout(
    title_text=(
        "Apariciones de contextos culturales "
        "en la colección permanente de numismática del"
        "<br>Museo Arqueológico Nacional"
        f"<br><sup>Total de registros: {total_reg} | "
        f"Total de cadenas únicas: {total_cadenas}</sup>"
    ),

    width=1000,
    height=800,

    margin=dict(t=120)
)

fig.update_traces(
    sort=False,
    leaf_opacity=1,
    opacity=1,
    selector=dict(type='icicle')
)

# =============================================================================
# EXPORTACIÓN
# =============================================================================

fig.write_html(OUTPUT_ICICLE)