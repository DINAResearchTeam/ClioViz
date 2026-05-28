# Librerías necesarias
import pandas as pd
import numpy as np
import re
import math
import geopandas as gpd

def leer_df(type):
    """
    Lee el dataframe de contexto, errores o incertidumbre según el tipo especificado.
    Args:
        type (str): El tipo de dataframe a leer. Puede ser "contexto", "errores" o "incertidumbre".
    Returns:
        pd.DataFrame: El dataframe leído según el tipo especificado.
    """
    if type == "contexto":
        sheet = "contexto"
    elif type == "errores":
        sheet = "No aparece en Tesauro-contextos"
    else:
        sheet = "Incertidumbre-contextos"

    CONTEXTOS = ("../datos/creados/CasodePrueba-Numismatica_amb.xlsx")
    
    cont = pd.read_excel(CONTEXTOS, sheet_name=sheet)
    cont.columns = cont.columns.str.strip()
    cont = cont[cont["PRIMER NIVEL"].notnull()]
    cont["PRIMER NIVEL"] = cont["PRIMER NIVEL"].str.strip()

    cont["PRIMER NIVEL"] = cont["PRIMER NIVEL"].replace("Edad Modera", "Edad Moderna")
    cont["PRIMER NIVEL"] = cont["PRIMER NIVEL"].apply(lambda x: x.title())

    cont = cont.rename(columns={"Unnamed: 1": "where"})
    cont["where"] = cont["where"].apply(lambda x: re.sub("\n", "", x).strip() if pd.notnull(x) else x)
        
    cont["place"] = cont.apply(lambda x: x["where"].split(":")[1].strip() if pd.notnull(x["where"]) else x["where"], axis=1)
    cont["place"] = cont["place"].apply(lambda x: x.replace("Canarías", "Canarias").strip() if pd.notnull(x) else x)

    # eliminar columnas que empiezan por "Unnamed"
    cont = cont.loc[:, ~cont.columns.str.startswith("Unnamed")]

    # Crear la columna "id" concatenando las columnas de niveles y CNTT, separadas por guiones bajos
    cont["id"] = cont.apply(lambda x: str(x["CNTT"]) + "_" + str(x["PRIMER NIVEL"]) + "_" + str(x["SEGUNDO NIVEL"]) + "_" + str(x["TERCER NIVEL"]) + "_" + str(x["CUARTO NIVEL"]) + "_" + str(x["QUINTO NIVEL"]) + "_" + str(x["SEXTO NIVEL"]), axis=1)
    cont["id"] = cont["id"].str.replace(" ", "_").str.replace("__", "_").str.replace("__", "_").str.replace("__", "_").str.replace("__", "_").str.replace("__", "_")

    return cont


def crear_df(df, contextos, type, provincias, dict_names, order):
    df["CNTT"] = df["CNTT"].str.strip()
    contextos["CNTT"] = contextos["CNTT"].str.strip()
    cont_df = df.merge(contextos, on='CNTT', how='left')

    
    cont_df["PRIMER NIVEL"] = cont_df["PRIMER NIVEL"].str.strip().apply(lambda x: dict_names.get(x, x))


    cont_df["PRIMER NIVEL"] = pd.Categorical(cont_df["PRIMER NIVEL"], categories=[dict_names.get(level, level) for level in order], ordered=True)
    cont_df["type"] = type
    titles = cont_df['PRIMER NIVEL'].sort_values(ascending=False).tolist()

    df1 = cont_df.copy(deep=True)
    df1 = df1[df1["CNTT"].notnull()]
    # df2 =
    df1 = df1.groupby(['provincia', 'PRIMER NIVEL']).size().reset_index(name='count').sort_values(by='count', ascending=False)
    df1["count"] = df1["count"].replace(0, np.nan)

    all_cnt = cont_df.groupby(['type', 'PRIMER NIVEL']).size().reset_index(name='count')
    all_cnt["textcnt"] = all_cnt.apply(lambda x: f"{x['PRIMER NIVEL']} ({'{:,.0f}'.format(x['count'])} {'object' if x['count'] == 1 else 'objects'})", axis=1)
    all_cnt = all_cnt.drop(columns=['count'])

    museos = cont_df.groupby(['provincia', 'PRIMER NIVEL', "DMUSEO"]).size().reset_index(name='count').sort_values(by='count', ascending=False)
    museos = museos[museos["count"] > 0]
    museos["text"] = museos.apply(lambda x: f"{x['DMUSEO'].strip()}: {'{:.0f}'.format(x['count'])} {'object' if x['count'] == 1 else 'objects'}", axis=1)

    museos_aux = museos.groupby(['provincia', 'PRIMER NIVEL']).agg({
        'text': lambda x: '<ul>' + ''.join(f'<li>{item}</li>' for item in x) + '</ul>'
    }).reset_index()

    df1 = df1.merge(all_cnt, on='PRIMER NIVEL', how='left')

    df1["percentage"] = df1["count"] / df1.groupby('PRIMER NIVEL')['count'].transform('sum') * 100
    df1 = df1.sort_values(by='PRIMER NIVEL', key=lambda x: x.map({k: i for i, k in enumerate(order)}))
    df1 = df1.merge(provincias, left_on='provincia', right_on='provincia', how='left')

    df1["text"] = df1.apply(lambda x: f"{museos_aux[(museos_aux['provincia'] == x['provincia']) & (museos_aux['PRIMER NIVEL'] == x['PRIMER NIVEL'])]['text'].values[0] if not museos_aux[(museos_aux['provincia'] == x['provincia']) & (museos_aux['PRIMER NIVEL'] == x['PRIMER NIVEL'])].empty else np.nan}", axis=1)


    # df1 = df1.dissolve(by='provincia')

    # añadir para cada PRIMER NIVEL, las provincias que faltan

    for lev in df1["PRIMER NIVEL"].unique():
        df2 = df1[df1["PRIMER NIVEL"] == lev]
        p = provincias[~provincias["provincia"].isin(df2["provincia"].unique())]
        # print(f"Provincias que faltan para {lev}: {p.shape[0]}")
        for n, row in p.iterrows():
            df1 = pd.concat([df1, pd.DataFrame({"provincia": row["provincia"],
                            "PRIMER NIVEL": lev,
                            "count": np.nan,
                            'text': np.nan,
                            'textcnt': all_cnt[all_cnt["PRIMER NIVEL"] == lev]["textcnt"].values[0] if not all_cnt[all_cnt["PRIMER NIVEL"] == lev].empty else np.nan,
                            "percentage": np.nan,
                                "geometry": [row["geometry"]]}, index=[0])], ignore_index=True)

    df1 = df1.reset_index(drop=True)

    df1 = gpd.GeoDataFrame(df1, geometry='geometry')

    # add crs to df1
    df1.crs = provincias.crs

    return df1

def año_a_siglo(año, unidad=None):
    """
    Convierte un año dado en su correspondiente siglo, teniendo en cuenta la unidad de tiempo (BP, Ma o años normales).
     Args:
        año (int o float): El año a convertir.
        unidad (str, opcional): La unidad de tiempo del año. Puede ser "BP", "Ma" o None para años normales. Por defecto es None.
        Returns:
        str: El siglo correspondiente al año dado, en formato romano y con la indicación de a.C. o d.C. si es necesario.
        """
    
    if unidad == "BP":
        # eliminar puntos decimales
        año = str(año).split(".")[0].split(",")[0]
        # Convertir BP a años d.C. o a.C.
        año = 1950 - abs(int(año))
        if año < 0:
            siglo = math.ceil(abs(año) / 100)
            return f"{arabigo_a_romano(siglo)} a.C."
        elif año == 0:
            return "1 a.C."
        else:
            siglo = math.ceil(año / 100)
            return f"{arabigo_a_romano(siglo)} d.C."
    elif unidad == "Ma":
        # Manejar millones de años
        return f"{año} millones de años"
    else:
        año = int(año)
        # Manejar años normales (a.C. o d.C.)
        if año == 0:
            return ""
        if año < 0:
            siglo = math.ceil(abs(año) / 100)
            return f"{arabigo_a_romano(siglo)} a.C."
        else:
            siglo = math.ceil(año / 100)
            return f"{arabigo_a_romano(siglo)} d.C."

def arabigo_a_romano(num):
    """
    Convierte un número arábigo a su representación en números romanos.
    Args:
        num (int): El número arábigo a convertir.
    Returns:
        str: La representación en números romanos del número dado.
    """

    val = [
        1000, 900, 500, 400,
        100, 90, 50, 40,
        10, 9, 5, 4,
        1
    ]
    syms = [
        "M", "CM", "D", "CD",
        "C", "XC", "L", "XL",
        "X", "IX", "V", "IV",
        "I"
    ]
    romano = ""
    i = 0
    while num > 0:
        for _ in range(num // val[i]):
            romano += syms[i]
            num -= val[i]
        i += 1
    return romano

def siglo_romano_a_numero(siglo_romano: str, es_ac: bool = False) -> int:
    # Diccionario para convertir números romanos a enteros
    valores_romanos = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50,
        'C': 100, 'D': 500, 'M': 1000
    }

    # Convertir el número romano a entero
    def romano_a_entero(romano: str) -> int:
        total = 0
        prev = 0
        for letra in reversed(romano.upper()):
            valor = valores_romanos.get(letra, 0)
            if valor < prev:
                total -= valor
            else:
                total += valor
                prev = valor
        return total

    numero = romano_a_entero(siglo_romano)

    # Si es a.C., se representa como negativo
    return -numero if es_ac else numero

def cuarto_del_siglo(año):
    # Determinar el siglo en el que está el año
    siglo = (año - 1) // 100 + 1
    siglo = arabigo_a_romano(siglo) + " d.C." if año > 0 else arabigo_a_romano(abs(siglo)) + " a.C."
    
    # Determinar el año dentro del siglo
    año_dentro_del_siglo = año % 100 if año % 100 != 0 else 100
    
    # Determinar en qué cuarto de siglo está el año
    if 1 <= año_dentro_del_siglo <= 25:
        cuarto, num = "primer", 1
    elif 26 <= año_dentro_del_siglo <= 50:
        cuarto, num = "segundo", 2
    elif 51 <= año_dentro_del_siglo <= 75:
        cuarto, num = "tercer", 3
    else:
        cuarto, num = "cuarto", 4
    
    return num, siglo, f"{num}/4 S.{siglo}"

def cuarto_del_siglo_en(año):
    # Determinar el siglo en el que está el año
    siglo = (año - 1) // 100 + 1
    # siglo = str(siglo) + " B.C." if año < 0 else str(siglo) + " A.D."
    
    # Determinar el año dentro del siglo
    año_dentro_del_siglo = año % 100 if año % 100 != 0 else 100
    
    # Determinar en qué cuarto de siglo está el año
    if 1 <= año_dentro_del_siglo <= 25:
        cuarto, num, label_part = "primer", 1, "1st"
    elif 26 <= año_dentro_del_siglo <= 50:
        cuarto, num, label_part = "segundo", 2, "2nd"
    elif 51 <= año_dentro_del_siglo <= 75:
        cuarto, num, label_part = "tercer", 3, "3rd"
    else:
        cuarto, num, label_part = "cuarto", 4, "4th"
        
    century_label = str(siglo) + ("st" if siglo == 1 else "nd" if siglo == 2 else "rd" if siglo == 3 else "th")
    
    return num, str(siglo), f"{label_part} quarter {century_label} century"

def load_limpiar_tiempo(path):
    """
    Limpia y procesa el dataframe de tiempo, extrayendo información relevante sobre los periodos históricos.
    Args:
        path (str): La ruta al archivo de tiempo.
    Returns:
        pd.DataFrame: El dataframe de tiempo limpio y procesado, con columnas adicionales para el tipo de dato, unidades y siglos correspondientes.
    """

    tiempo = pd.read_excel(path)
    tiempo.drop(columns=["Type"], inplace=True)
    tiempo["Fin"] = tiempo["Fin"].fillna(np.nan)
    tiempo["Periodo"] = np.where(np.nan_to_num(tiempo["Fin"]) == 0, "No", "Si")
    tiempo = tiempo[tiempo["Inicio"].notnull()]
    
    tiempo["Tipo_data"] = ["Periodo" if pd.notnull(row["Fin"])
    else "Aproximación" if "," in str(row["Inicio"]) or str(abs(int(row["Inicio"]))) + '[ca]' in row["DATA"] or
                          str(abs(int(row["Inicio"]))) + ' [ca]' in row["DATA"] or 
                          str(abs(int(row["Inicio"]))) + '[ac][ca]' in row["DATA"] 
                          else
                        "Único"
                       for num, row in tiempo.iterrows()
                       ]

    # Aplicar la función lambda para extraer el año de inicio y fin del periodo, dependiendo del formato de la columna "DATA"
    tiempo["D"] = tiempo.apply(lambda x: x["DATA"].split()[0] if "442-698" in x["DATA"] else x["D"], axis=1)
    # Unificar el formato de la columna "D" para los periodos, reemplazando "=" por "-" y tomando solo la primera parte antes de la coma
    tiempo["D"] = tiempo.apply(lambda x: x["D"].replace("=", "-").split(",")[0] if x["Tipo_data"] == "Periodo" else x["D"], axis=1)

    # Aplicar la función lambda para extraer el año de inicio y fin del periodo, dependiendo del formato de la columna "D"
    tiempo["Inicio"] = tiempo.apply(lambda x: str(x["D"].split("-")[0].split("/")[-1]) if "/" in x["D"] else str(x["D"].split("-")[0]) if "-" in x["D"] else str(x["Inicio"]) if x["Inicio"] else pd.nan  , axis=1)
    tiempo["Inicio"] = tiempo.apply(lambda x: -abs(int(x["Inicio"])) if x["Inicio"] + "[ac]" in x["DATA"] else x["Inicio"], axis=1)

    # Aplicar la función lambda para extraer el año de inicio y fin del periodo, dependiendo del formato de la columna "D"
    tiempo["Fin"] = tiempo.apply(lambda x: int(x["D"].split("-")[-1].split("/")[-1]) if "/" in x["D"] else int(x["D"].split("-")[-1]) if "-" in x["D"] else x["Fin"] if x["Fin"] else pd.nan, axis=1)
    tiempo["Fin"] = tiempo.apply(lambda x: -abs(int(x["Fin"])) if pd.notnull(x["Fin"]) and str(abs(int(x["Fin"]))) + "[ac]" in x["DATA"] else x["Fin"], axis=1)

    # Obtener el tipo de dato (Periodo, Aproximación o Único) dependiendo de si la columna "Fin" tiene un valor o no, y si la columna "Inicio" tiene un formato específico que indique una aproximación
    tiempo["Tipo_data"] = ["Periodo" if pd.notnull(row["Fin"])
        else "Aproximación" if "," in str(row["Inicio"]) or str(abs(int(row["Inicio"]))) + '[ca]' in row["DATA"] or
                            str(abs(int(row["Inicio"]))) + ' [ca]' in row["DATA"] or
                            str(abs(int(row["Inicio"]))) + '[ac][ca]' in row["DATA"] 
                            else
                            "Único"
                        for num, row in tiempo.iterrows()
                        ]             

    # Aplicar la función lambda para extraer las unidades de tiempo (BP o Ma) dependiendo del formato de la columna "DATA"
    tiempo["Unidades Inicio"] = tiempo.apply(
        lambda x: "BP" if "[BP]" in str(x["DATA"]) else "Ma" if "[Ma]" in str(x["DATA"]) else "",
        axis=1
    )

    tiempo["Unidades Fin"] = tiempo.apply(
        lambda x: "BP" if "[BP]" in str(x["DATA"]) else "Ma" if "[Ma]" in str(x["DATA"]) else "",
        axis=1
    )

    # Aplicar la función lambda para convertir los años de inicio y fin a siglos, dependiendo de las unidades de tiempo correspondientes
    tiempo["Siglo Inicio"] = tiempo[['Inicio', 'Unidades Inicio']].apply(
        lambda x: año_a_siglo(x["Inicio"], x["Unidades Inicio"]),
        axis=1
    )

    tiempo["Siglo Fin"] = tiempo[['Fin', 'Unidades Fin']].apply(
        lambda x: año_a_siglo(x["Fin"], x["Unidades Fin"]) if not pd.isnull(x["Fin"]) else "",
        axis=1
    )

    return tiempo
