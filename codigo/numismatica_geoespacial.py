# =============================================================================
# IMPORTS
# =============================================================================

import re, os
import numpy as np
import pandas as pd
import geopandas as gpd

import folium
from folium import plugins

import plotly.graph_objects as go

import branca.colormap as cm

from utils import leer_df, load_limpiar_tiempo


# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

# Rutas de entrada
PATH_DATASET = r"../datos/FMUS.xlsx"
PATH_TIEMPO = r"../datos/creados/tiempo_nuevo4.xlsx"
PATH_PROVINCIAS = r"../datos/creados/provincias.geojson"
PATH_MUSEOS = r"../datos/creados/museos_prov1.csv"



if not os.path.exists("./outputs"):
    os.makedirs("./outputs")

# Rutas de salida
OUTPUT_MAP = r"./outputs/numismatica_mapa.html"
OUTPUT_HEATMAP = r"./outputs/numismatica_heatmap.html"

# Orden cronológico de periodos históricos
ORDER = [
    "Prehistoria",
    "Protohistoria",
    "Edad Antigua",
    "Edad Media",
    "Edad Moderna",
    "Edad Contemporánea"
]

# Traducción al inglés
DICT_NAMES = {
    "Prehistoria": "Prehistory",
    "Protohistoria": "Protohistory",
    "Edad Antigua": "Ancient Age",
    "Edad Media": "Middle Ages",
    "Edad Moderna": "Modern Age",
    "Edad Contemporánea": "Contemporary Age"
}

# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def clean_object_name(value):
    """
    Normaliza el nombre del objeto.

    Parameters
    ----------
    value : str

    Returns
    -------
    str
    """
    if isinstance(value, str):
        return (
            value.strip()
            .replace("Moeda", "Moneda")
            .title()
        )
    return value


def clean_context_column(df):
    """
    Limpia espacios en la columna 'PRIMER NIVEL'.

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


def normalize_province_name(name):
    """
    Normaliza nombres de provincias.

    Parameters
    ----------
    name : str

    Returns
    -------
    str
    """
    if re.findall(r"[A-Z][^A-Z]*", name):
        parts = re.findall(r"[A-Z][^A-Z]*", name)

        text = " ".join(parts)

        if text.startswith("Provinceof"):
            parts = [parts[1]]

        elif text.startswith("Cdad."):
            parts = [re.sub("Cdad.", "Ciudad", text)]

        elif text.startswith("Valencia"):
            parts = [re.sub("e", "è", text)]

        elif text.startswith("La"):
            parts = [re.sub("La", "A", text)]

    else:
        exact_match = re.compile(r"[^Ä-Ž]\w+", re.UNICODE)
        parts = exact_match.findall(name)

    return re.sub(r"\s+", " ", " ".join(parts))

def create_tooltip_html(row, type, etapa):
    if pd.isnull(row['count']):
        return f"""
        <b>{row['provincia']}</b>:<br>
        Sin objetos
        """
    message = "objetos" if row['count'] > 1 else "objeto"
    return f"""
    <b>Tipología periodo:</b> {type}<br>
    <b>Periodo:</b> {etapa}<br>
    <b>Provincia: {row['provincia']}</b> - {'{:,.0f}'.format(row['count'])} {message} ({row['percentage']:.2f}%)<br>
    <b>Cantidad por museo:</b><br>
    {row['text'] if pd.notnull(row['text']) else 'No disponible'}
    """


# =============================================================================
# CARGA DE DATOS
# =============================================================================

print("Cargando dataset...")

data = pd.read_excel(PATH_DATASET)

# Copia de trabajo
numismatica = data.copy(deep=True)

# Normalización de nombres de objetos
numismatica["OBJE"] = numismatica["OBJE"].apply(clean_object_name)

# Filtrado de registros numismáticos
numismatica = numismatica[
    (
        numismatica["CLAS"].str.contains(
            "numismática",
            case=False,
            na=False
        )
    )
    &
    (numismatica["OBJE"] == "Moneda")
]

print(f"Registros numismáticos: {numismatica.shape[0]}")


# =============================================================================
# CARGA DE CONTEXTOS
# =============================================================================

todo = clean_context_column(leer_df("contexto"))
errores = clean_context_column(leer_df("errores"))
amb = clean_context_column(leer_df("ambigüedad"))

# Eliminar errores y ambigüedades del conjunto principal
todo = todo[~todo["id"].isin(errores["id"])]
todo = todo[~todo["id"].isin(amb["id"])]

# Mantener columnas necesarias
todo = todo[["CNTT", "PRIMER NIVEL"]]
errores = errores[["CNTT", "PRIMER NIVEL"]]
amb = amb[["CNTT", "PRIMER NIVEL"]]

# Corrección manual
errores.loc[
    (
        (errores["PRIMER NIVEL"] == "Prehistoria")
        &
        (errores["CNTT"].str.contains("Mauritania"))
    ),
    "PRIMER NIVEL"
] = "Edad Antigua"

# Reintegrar errores corregidos
todo = pd.concat([todo, errores], axis=0).reset_index(drop=True)


# =============================================================================
# AMBIGÜEDADES
# =============================================================================

# Mantener únicamente contextos ambiguos con una sola categoría
unique_periods = (
    amb.groupby("CNTT", observed=True)
    .agg({"PRIMER NIVEL": pd.Series.nunique})
    .reset_index()
)

unique_periods = unique_periods[
    unique_periods["PRIMER NIVEL"] == 1
]

amb_cont = (
    amb[
        amb["CNTT"].isin(unique_periods["CNTT"])
    ]
    .drop_duplicates(["CNTT", "PRIMER NIVEL"])
    .reset_index(drop=True)
)


# =============================================================================
# DATOS GEOGRÁFICOS
# =============================================================================

print("Cargando provincias...")

provincias = gpd.read_file(PATH_PROVINCIAS)

print("Cargando museos...")

museos = pd.read_csv(
    PATH_MUSEOS,
    sep=";",
    encoding="latin1",
    decimal=","
)

# Normalización de nombres de provincias
museos["provincia"] = museos["provincia"].apply(
    normalize_province_name
)


# =============================================================================
# PREPARACIÓN DE DATOS
# =============================================================================

def create_geodataframe(
    df: pd.DataFrame,
    contextos: pd.DataFrame,
    label_type: str
) -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame aggregated by province and period,
    preserving all functionality from the original implementation.

    Parameters
    ----------
    df : pd.DataFrame
        Main dataframe containing object records.

    contextos : pd.DataFrame
        Context dataframe containing CNTT mappings.

    label_type : str
        Label assigned to the resulting dataframe.

    Returns
    -------
    geopandas.GeoDataFrame
    """

    # ------------------------------------------------------------------
    # Clean CNTT fields
    # ------------------------------------------------------------------
    df = df.copy()
    contextos = contextos.copy()

    df["CNTT"] = df["CNTT"].str.strip()
    contextos["CNTT"] = contextos["CNTT"].str.strip()

    # ------------------------------------------------------------------
    # Merge context information
    # ------------------------------------------------------------------
    cont_df = df.merge(
        contextos,
        on="CNTT",
        how="left"
    )

    # ------------------------------------------------------------------
    # Normalize PRIMER NIVEL labels
    # ------------------------------------------------------------------
    cont_df["PRIMER NIVEL"] = (
        cont_df["PRIMER NIVEL"]
        .str.strip()
        .apply(lambda x: DICT_NAMES.get(x, x))
    )

    # ------------------------------------------------------------------
    # Ordered categorical
    # ------------------------------------------------------------------
    ordered_categories = [
        DICT_NAMES.get(level, level)
        for level in ORDER
    ]

    cont_df["PRIMER NIVEL"] = pd.Categorical(
        cont_df["PRIMER NIVEL"],
        categories=ordered_categories,
        ordered=True
    )

    cont_df["type"] = label_type

    # ------------------------------------------------------------------
    # Remove null CNTT
    # ------------------------------------------------------------------
    filtered_df = cont_df[
        cont_df["CNTT"].notnull()
    ].copy()

    # ------------------------------------------------------------------
    # Main aggregation
    # ------------------------------------------------------------------
    grouped = (
        filtered_df
        .groupby(
            ["provincia", "PRIMER NIVEL"], observed=True
        )
        .size()
        .reset_index(name="count")
        .sort_values(
            by="count",
            ascending=False
        )
    )

    grouped["count"] = grouped["count"].replace(
        0,
        np.nan
    )

    # ------------------------------------------------------------------
    # Total counts by level
    # ------------------------------------------------------------------
    all_counts = (
        cont_df
        .groupby(
            ["type", "PRIMER NIVEL"], observed=True
        )
        .size()
        .reset_index(name="count")
    )

    all_counts["textcnt"] = all_counts.apply(
        lambda row:
        f"{row['PRIMER NIVEL']} "
        f"({row['count']:,.0f} "
        f"{'object' if row['count'] == 1 else 'objects'})",
        axis=1
    )

    all_counts = all_counts.drop(columns="count")

    # ------------------------------------------------------------------
    # Museum aggregation
    # ------------------------------------------------------------------
    museums = (
        cont_df
        .groupby(
            ["provincia", "PRIMER NIVEL", "DMUSEO"], observed=True
        )
        .size()
        .reset_index(name="count")
        .sort_values(
            by="count",
            ascending=False
        )
    )

    museums = museums[
        museums["count"] > 0
    ]

    museums["text"] = museums.apply(
        lambda row:
        f"{row['DMUSEO'].strip()}: "
        f"{row['count']:.0f} "
        f"{'object' if row['count'] == 1 else 'objects'}",
        axis=1
    )

    # ------------------------------------------------------------------
    # HTML tooltip aggregation
    # ------------------------------------------------------------------
    museums_aux = (
        museums
        .groupby(
            ["provincia", "PRIMER NIVEL"], observed=True
        )
        .agg({
            "text":
            lambda values:
            # "<ul>"
            # + 
            "<br>".join(
                f"<li>{item}</li>"
                for item in values
            )
            # + "</ul>"
        })
        .reset_index()
    )

    # ------------------------------------------------------------------
    # Merge global counts
    # ------------------------------------------------------------------
    grouped = grouped.merge(
        all_counts,
        on="PRIMER NIVEL",
        how="left"
    )

    # ------------------------------------------------------------------
    # Percentage calculation
    # ------------------------------------------------------------------
    grouped["percentage"] = (
        grouped["count"]
        /
        grouped.groupby(
            "PRIMER NIVEL", observed=True
        )["count"].transform("sum")
    ) * 100

    # ------------------------------------------------------------------
    # Sort according to ORDER
    # ------------------------------------------------------------------
    order_mapping = {
        category: idx
        for idx, category in enumerate(ORDER)
    }

    grouped = grouped.sort_values(
        by="PRIMER NIVEL",
        key=lambda col: col.map(order_mapping)
    )

    # ------------------------------------------------------------------
    # Merge geometries
    # ------------------------------------------------------------------
    grouped = grouped.merge(
        provincias,
        on="provincia",
        how="left"
    )

    # ------------------------------------------------------------------
    # Add tooltip text
    # ------------------------------------------------------------------
    grouped["text"] = grouped.apply(
        lambda row:
        museums_aux[
            (
                museums_aux["provincia"]
                == row["provincia"]
            )
            &
            (
                museums_aux["PRIMER NIVEL"]
                == row["PRIMER NIVEL"]
            )
        ]["text"].values[0]
        if not museums_aux[
            (
                museums_aux["provincia"]
                == row["provincia"]
            )
            &
            (
                museums_aux["PRIMER NIVEL"]
                == row["PRIMER NIVEL"]
            )
        ].empty
        else np.nan,
        axis=1
    )

    # ------------------------------------------------------------------
    # Add missing provinces for each level
    # ------------------------------------------------------------------
    for level in grouped["PRIMER NIVEL"].unique():

        existing = grouped[
            grouped["PRIMER NIVEL"] == level
        ]

        missing_provinces = provincias[
            ~provincias["provincia"].isin(
                existing["provincia"].unique()
            )
        ]

        for _, province_row in missing_provinces.iterrows():

            grouped = pd.concat(
                [
                    grouped,
                    pd.DataFrame({
                        "provincia": [
                            province_row["provincia"]
                        ],
                        "PRIMER NIVEL": [level],
                        "count": [np.nan],
                        "text": [np.nan],
                        "textcnt": [
                            all_counts[
                                all_counts["PRIMER NIVEL"]
                                == level
                            ]["textcnt"].values[0]
                            if not all_counts[
                                all_counts["PRIMER NIVEL"]
                                == level
                            ].empty
                            else np.nan
                        ],
                        "percentage": [np.nan],
                        "geometry": [
                            province_row["geometry"]
                        ]
                    })
                ],
                ignore_index=True
            )

    # ------------------------------------------------------------------
    # Reset index
    # ------------------------------------------------------------------
    grouped = grouped.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Create GeoDataFrame
    # ------------------------------------------------------------------
    gdf = gpd.GeoDataFrame(
        grouped,
        geometry="geometry"
    )

    gdf.crs = provincias.crs

    return gdf

# =============================================================================
# FILTRADO DE MUSEOS
# =============================================================================

museum_counts = (
    numismatica[numismatica["CNTT"].notnull()]
    ["DMUSEO"]
    .value_counts()
)

museum_counts = museum_counts[museum_counts > 50]

selected_museums = museum_counts.index.tolist()

df_filtered = numismatica[
    numismatica["DMUSEO"].isin(selected_museums)
]

df_filtered = df_filtered[
    df_filtered["CNTT"].notnull()
]

df_filtered["CNTT"] = df_filtered["CNTT"].str.strip()

# Añadir provincia
df_filtered = df_filtered.merge(
    museos,
    left_on="DMUSEO",
    right_on="museo",
    how="left"
)


# =============================================================================
# CREACIÓN DE DATAFRAMES FINALES
# =============================================================================

df_univocal = create_geodataframe(
    df_filtered,
    todo,
    label_type="Periodos de etiqueta unívoca"
)

df_univocal["type"] = "Periodos de etiqueta unívoca"


df_ambiguous = create_geodataframe(
    df_filtered,
    amb_cont,
    label_type="Periodos de etiqueta ambigua"
)
df_ambiguous["type"] = "Periodos de etiqueta ambigua"

df_final = pd.concat(
    [df_univocal, df_ambiguous],
    ignore_index=True
)


# =============================================================================
# MAPA INTERACTIVO (FOLIUM)
# =============================================================================

print("Generando mapa interactivo...")


css = """
.legend.leaflet-control{
    background-color: white !important;
    border: 1px solid black !important;
    margin: 10px !important;
    padding: 10px !important;
    border-radius: 5px !important;}

"""

# CSS crítico para radio buttons reales
exclusive_css = """
/* Ocultar checkboxes nativos */
.leaflet-control-layers-overlays input[type="checkbox"] {
    display: none !important;
}

.leaflet-control-layers-selector {
    margin-right: 5px;
    margin-bottom: 5px;
    align-items: center;
}


/* Estilo de selección */
.leaflet-control-layers-overlays input:checked + label:before {
    background: #0078A8;
    border-color: #0078A8;
    box-shadow: inset 0 0 0 3px white;
}

/* Alinear texto correctamente */
.leaflet-control-layers-overlays label {
    display: flex !important;
    align-items: center !important;
    cursor: pointer !important;
}
.legend.leaflet-control{
    background-color: white !important;
    border: 1px solid black !important;
    margin: 10px !important;
    padding: 10px !important;
    border-radius: 5px !important;}
"""

m = folium.Map(
    location=[40.4637, -3.7492],
    zoom_start=6
)

# Escala de color
colormap = cm.linear.YlOrRd_05.scale(0, 100)
colormap.caption = "Porcentaje de objetos por provincia"

m.get_root().header.add_child(folium.Element(f"<style>{css}</style>"))

with open("css_map.css", "r", encoding="utf-8") as f:
    css_content = f.read()

style = f"<style type='text/css'>{css_content}</style>"
m.get_root().header.add_child(folium.Element(style))

m.add_child(colormap)

# Crear capas
dict_types = {}

for label_type, df_map in zip(
    df_final["type"].unique(),
    [df_univocal, df_ambiguous]
):

    layers = []

    for period in df_map["PRIMER NIVEL"].unique():

        layer = folium.FeatureGroup(
            name=period,
            overlay=False
        )

        subset = df_map[
            df_map["PRIMER NIVEL"] == period
        ]

        for _, row in subset.iterrows():

            if pd.isnull(row["geometry"]):
                continue

            color = (
                "lightgray"
                if pd.isnull(row["percentage"])
                else colormap(row["percentage"])
            )

            folium.GeoJson(
                row["geometry"],
                tooltip=folium.Tooltip(
                    create_tooltip_html(
                        row,
                        label_type,
                        period
                    )
                ),
                style_function=lambda x, color=color: {
                    "weight": 0.3,
                    "fillOpacity": 1,
                    "color": "black",
                    "fillColor": color,
                }
            ).add_to(layer)

        layer.add_to(m)
        layers.append(layer)

    dict_types[label_type] = layers

# Control de capas
plugins.GroupedLayerControl(
    groups=dict_types,
    collapsed=False,
    exclusive_groups=False
).add_to(m)


# JavaScript para exclusividad total
exclusive_js = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.leaflet-control-layers-overlays');

    // Marcar el primer input como checked por defecto
    const firstInput = container.querySelector('input[type="radio"]');
    if (firstInput) {
        firstInput.checked = true;
    }
    
    function enforceExclusivity(event) {
        const allInputs = container.querySelectorAll('input');
        if (event.target.checked) {
            allInputs.forEach(input => {
                if (input !== event.target) input.checked = false;
            });
        }
    }
    
    // Convertir a radio buttons virtuales
    container.querySelectorAll('input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', enforceExclusivity);
        // Convertir checkbox a radio button
        const label = input.nextElementSibling;
        if (label) {
            label.style.alignItems = 'center';  // Alinear verticalmente
            input.type = 'radio';  // Cambiar tipo a radio
            // Asignar su nombre para agrupar
            input.name = 'exclusive-group';  // Agrupar todos los inputs
        }
    });

    // Selecciona el primer checkbox utilizando querySelector
    let primerCheckbox = document.querySelector('input[type="radio"]');

    // Observar cambios dinámicos
    new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            mutation.addedNodes.forEach(node => {
                if (node.tagName === 'INPUT') {
                    node.addEventListener('change', enforceExclusivity);
                }
            });
        });
    }).observe(container, { childList: true, subtree: true });
});
</script>
"""

# Añadir JavaScript al mapa
m.get_root().html.add_child(folium.Element(exclusive_js))

# Css to change span
css_span = """
.leaflet-control-layers-selector.span {
    display: content;
}
"""

# Añadir CSS para cambiar el span
m.get_root().html.add_child(folium.Element(f"<style>{exclusive_css}</style>"))

# Título del mapa
titulo_html = """<div style="position:absolute; top:10px; left:50%; transform:translateX(-50%);
                z-index:1000; background:white; padding:5px 15px; border:2px solid black;
                border-radius:5px; font-size:16px; font-weight:bold;text-align:center;">
                Relación de periodos según museo (> 50 registros) agrupados por provincia,<br>para categoria clasificación "numismática" y tipo de objeto "moneda"<br>
                en CER.es"
                </div>
                """
m.get_root().html.add_child(folium.Element(titulo_html))

# Guardar mapa
m.save(OUTPUT_MAP)

print(f"Mapa guardado en: {OUTPUT_MAP}")


# =============================================================================
# HEATMAP INTERACTIVO (PLOTLY)
# =============================================================================

print("Generando heatmap...")


# ----------------------------------------------------------------------
# Summary dataframe creation
# ----------------------------------------------------------------------
def create_summary_dataframe(
    df: pd.DataFrame,
    contextos: pd.DataFrame,
    label_type: str
) -> pd.DataFrame:
    """
    Create aggregated dataframe by historical period.
    """

    # --------------------------------------------------------------
    # Clean CNTT columns
    # --------------------------------------------------------------
    df = df.copy()
    contextos = contextos.copy()

    df["CNTT"] = df["CNTT"].str.strip()
    contextos["CNTT"] = contextos["CNTT"].str.strip()

    # --------------------------------------------------------------
    # Merge contextual information
    # --------------------------------------------------------------
    cont_df = df.merge(
        contextos,
        on="CNTT",
        how="left"
    )

    # --------------------------------------------------------------
    # Ordered categorical period
    # --------------------------------------------------------------
    cont_df["PRIMER NIVEL"] = pd.Categorical(
        cont_df["PRIMER NIVEL"],
        categories=ORDER,
        ordered=True
    )

    cont_df["type"] = label_type

    # --------------------------------------------------------------
    # Filter valid CNTT
    # --------------------------------------------------------------
    filtered_df = cont_df[
        cont_df["CNTT"].notnull()
    ].copy()

    # --------------------------------------------------------------
    # Aggregate counts
    # --------------------------------------------------------------
    summary_df = (
        filtered_df
        .groupby("PRIMER NIVEL", observed=True)
        .size()
        .reset_index(name="count")
        .sort_values(
            by="count",
            ascending=False
        )
    )

    summary_df["count"] = summary_df["count"].replace(
        0,
        np.nan
    )

    # --------------------------------------------------------------
    # Total counts by type and level
    # --------------------------------------------------------------
    all_counts = (
        cont_df
        .groupby(
            ["type", "PRIMER NIVEL"], observed=True
        )
        .size()
        .reset_index(name="count")
    )

    all_counts["textcnt"] = all_counts.apply(
        lambda row:
        f"{row['PRIMER NIVEL']} "
        f"({row['count']:,.0f} "
        f"{'object' if row['count'] == 1 else 'objects'})",
        axis=1
    )

    all_counts = all_counts.drop(columns="count")

    # --------------------------------------------------------------
    # Museum aggregation
    # --------------------------------------------------------------
    museums_summary = (
        cont_df
        .groupby(
            ["PRIMER NIVEL", "DMUSEO"], observed=True
        )
        .size()
        .reset_index(name="count")
        .sort_values(
            by="count",
            ascending=False
        )
    )

    museums_summary = museums_summary[
        museums_summary["count"] > 0
    ]

    museums_summary["text"] = museums_summary.apply(
        lambda row:
        f"{row['DMUSEO'].strip()}: "
        f"{row['count']:.0f} "
        f"{'object' if row['count'] == 1 else 'objects'}",
        axis=1
    )

    # --------------------------------------------------------------
    # Merge totals
    # --------------------------------------------------------------
    summary_df = summary_df.merge(
        all_counts,
        on="PRIMER NIVEL",
        how="left"
    )

    # --------------------------------------------------------------
    # Percentage calculation
    # --------------------------------------------------------------
    summary_df["percentage"] = (
        summary_df["count"]
        /
        summary_df.groupby(
            "PRIMER NIVEL", observed=True
        )["count"].transform("sum")
    ) * 100

    # --------------------------------------------------------------
    # Sort by historical order
    # --------------------------------------------------------------
    order_mapping = {
        category: idx
        for idx, category in enumerate(ORDER)
    }

    summary_df = summary_df.sort_values(
        by="PRIMER NIVEL",
        key=lambda col: col.map(order_mapping)
    )

    # --------------------------------------------------------------
    # Final cleanup
    # --------------------------------------------------------------
    return summary_df.reset_index(drop=True)


# ----------------------------------------------------------------------
# Prepare numismatic dataframe
# ----------------------------------------------------------------------
df_numismatica = (
    numismatica[
        numismatica["CNTT"].notnull()
    ]
    .copy()
)

df_numismatica["CNTT"] = (
    df_numismatica["CNTT"]
    .str.strip()
)

df_numismatica = df_numismatica.merge(
    museos,
    left_on="DMUSEO",
    right_on="museo",
    how="left"
)


# ----------------------------------------------------------------------
# Create summary datasets
# ----------------------------------------------------------------------
df_todo = create_summary_dataframe(
    df=df_numismatica,
    contextos=todo,
    label_type="Periodos de etiqueta unívoca"
)

df_amb = create_summary_dataframe(
    df=df_numismatica,
    contextos=amb_cont,
    label_type="Periodos de etiqueta ambigua"
)

# ----------------------------------------------------------------------
# Assign labels
# ----------------------------------------------------------------------
df_todo["type"] = "Periodos de etiqueta unívoca"

df_amb["type"] = "Periodos de etiqueta ambigua"


# ----------------------------------------------------------------------
# Remove zero-object categories
# ----------------------------------------------------------------------
df_todo = (
    df_todo[
        ~df_todo["textcnt"].str.contains(
            r"\(0 objects\)",
            regex=True
        )
    ]
    .reset_index(drop=True)
)

df_amb = (
    df_amb[
        ~df_amb["textcnt"].str.contains(
            r"\(0 objects\)",
            regex=True
        )
    ]
    .reset_index(drop=True)
)


# ----------------------------------------------------------------------
# Combine final dataframe
# ----------------------------------------------------------------------
df_final = pd.concat(
    [df_todo, df_amb],
    ignore_index=True
)

df_final = (
    df_final[
        ~df_final["textcnt"].str.contains(
            r"\(0 objects\)",
            regex=True
        )
    ]
    .reset_index(drop=True)
)

# ----------------------------------------------------------------------
# Prepare dataframe
# ----------------------------------------------------------------------
all_combinations = pd.MultiIndex.from_product(
    [
        ORDER,
        df_final["type"].unique()
    ],
    names=[
        "PRIMER NIVEL",
        "type"
    ]
)

heatmap_df = (
    df_final
    .set_index(
        ["PRIMER NIVEL", "type"]
    )
    .reindex(all_combinations)
    .reset_index()
)

# Translate labels
heatmap_df["PRIMER NIVEL"] = (
    heatmap_df["PRIMER NIVEL"]
    .map(REVERSED_LABELS)
)

heatmap_df["type"] = (
    heatmap_df["type"]
    .map(TYPE_LABELS)
)

# Replace zeros with NaN
heatmap_df["count"] = (
    heatmap_df["count"]
    .replace(0, np.nan)
)


# ----------------------------------------------------------------------
# Pivot table
# ----------------------------------------------------------------------
pivot_df = heatmap_df.pivot_table(
    index="PRIMER NIVEL",
    columns="type",
    values="count",
    dropna=False
)


# ----------------------------------------------------------------------
# Totals for hover data
# ----------------------------------------------------------------------
row_totals = (
    heatmap_df
    .groupby("PRIMER NIVEL", observed=True)["count"]
    .sum()
)

column_totals = (
    heatmap_df
    .groupby("type", observed=True)["count"]
    .sum()
)

sorted_periods = sorted(
    pivot_df.index,
    key=lambda value:
    list(REVERSED_LABELS.values()).index(value)
)

customdata = [
    [
        [
            row_totals[period],
            column_totals[label_type]
        ]
        for label_type in pivot_df.columns
    ]
    for period in sorted_periods
]


# ----------------------------------------------------------------------
# Main heatmap
# ----------------------------------------------------------------------
fig = go.Figure()

fig.add_trace(
    go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale="YlOrRd",
        customdata=customdata,
        hoverongaps=False,
        hovertemplate=(
            "Period: %{y}<br>"
            "Type: %{x}<br>"
            "Count: %{z}<br>"
            "Total for period: %{customdata[0]}<br>"
            "Total for type: %{customdata[1]}"
            "<extra></extra>"
        ),
        colorbar=dict(
            title="Amount of objects",
            yanchor="bottom"
        )
    )
)


# ----------------------------------------------------------------------
# NaN overlay layer
# ----------------------------------------------------------------------
missing_periods = (
    heatmap_df[
        heatmap_df["count"].isna()
    ]["PRIMER NIVEL"]
    .unique()
)

nan_df = heatmap_df[
    heatmap_df["PRIMER NIVEL"]
    .isin(missing_periods)
]

nan_df = nan_df.pivot_table(
    index="PRIMER NIVEL",
    columns="type",
    values="count",
    dropna=False
)

# Fill NaNs for visualization
nan_df = nan_df.fillna(1)

# Keep only missing-value cells
nan_df[nan_df != 1] = 0


fig.add_trace(
    go.Heatmap(
        z=nan_df.values,
        x=nan_df.columns,
        y=nan_df.index,
        colorscale=[
            [0, "rgba(0, 0, 255, 0)"],
            [1, "lightgray"]
        ],
        hoverinfo="skip",
        hoverongaps=False,
        showscale=False
    )
)


# ----------------------------------------------------------------------
# Layout configuration
# ----------------------------------------------------------------------
fig.update_layout(
    title=dict(
        text=(
            "How many records classified as "
            "“numismática” and object type "
            "“moneda” are present in CER.es, "
            "according to their Cultural Context?"
        )
    ),
    autosize=True,
    xaxis=dict(
        fixedrange=True,
        ticklabelstandoff=5
    ),
    yaxis=dict(
        fixedrange=True,
        ticklabelstandoff=5,
        categoryarray=list(REVERSED_LABELS.values()),
        categoryorder="array"
    ),
    legend=dict(
        itemdoubleclick=False,
        itemclick=False
    )
)


# ----------------------------------------------------------------------
# Colorbar positioning
# ----------------------------------------------------------------------
colorbar_length = 0.8

fig.data[0].colorbar.update(
    yanchor="top",
    len=colorbar_length,
    y=0.5 + colorbar_length / 2
)


# ----------------------------------------------------------------------
# NaN legend item
# ----------------------------------------------------------------------
fig.add_trace(
    go.Scatter(
        x=[None],
        y=[None],
        mode="markers",
        marker=dict(
            size=10,
            color="lightgray"
        ),
        legendgroup="No data",
        showlegend=True,
        name="No data"
    )
)


# ----------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------
fig.write_html(
    OUTPUT_HEATMAP,
    include_plotlyjs="cdn",
    full_html=True
)

print(f"Heatmap guardado en: {OUTPUT_HEATMAP}")

print("Proceso completado.")