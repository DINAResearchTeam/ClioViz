# ClioViz

_Visualización avanzada de datos históricos mediante mapas multidimensionales y gráficos interactivos_

## Descripción

**ClioViz** es un proyecto de investigación de carácter multidisciplinar centrado en el análisis y la exploración visual de datos históricos y patrimoniales a gran escala. El proyecto desarrolla herramientas de visualización interactiva que permiten estudiar relaciones temporales, geográficas y semánticas entre bienes culturales.

La principal fuente de información utilizada es **CER.es**, el catálogo en línea de la Red Digital de Colecciones de Museos de España, que reúne más de 384.000 registros de bienes culturales procedentes de museos españoles.

## Objetivos

- Explorar nuevas estrategias para visualizar grandes volúmenes de datos desde una perspectiva centrada en el usuario.

- Mejorar la accesibilidad digital de los objetos de patrimonio cultural mediante herramientas innovadoras para investigación y difusión.

- Aprovechar el conocimiento generado para mejorar la visibilidad online del patrimonio español.

## Características de los datos espaciales y temporales

En el ámbito del Patrimonio Cultural, los datos espaciales y temporales presentan características específicas que los convierten en especialmente relevantes para el desarrollo de técnicas avanzadas de visualización dentro del proyecto **ClioViz**.

En particular, los datos patrimoniales suelen ser **heterogéneos**, presentan distintos niveles de **granularidad** y, con frecuencia, incorporan cierto grado de **incertidumbre o ambigüedad**. Estas características representan desafíos importantes para el análisis visual y la exploración interactiva de la información histórica.

| Aspecto                        | Espacio / Localización                                                                                                                                              | Tiempo                                                                                                                        |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Heterogeneidad**             | La localización puede expresarse mediante un topónimo (por ejemplo, _Madrid_) o mediante coordenadas geográficas (por ejemplo, _40.4165, -3.70256_).                | La información temporal puede aparecer en formato textual (por ejemplo, _siglo XVIII_) o numérico (por ejemplo, _1700–1799_). |
| **Granularidad**               | La ubicación de un objeto puede definirse de forma imprecisa, cubriendo regiones amplias (por ejemplo, _España_) o de forma más específica (por ejemplo, _Madrid_). | La variable temporal puede indicarse de manera aproximada (por ejemplo, _siglo XIV_) o específica (por ejemplo, _año 1359_).  |
| **Incertidumbre / Ambigüedad** | Un objeto puede asociarse a múltiples localizaciones cuando existe incertidumbre o diversidad de interpretaciones (por ejemplo, _España_ o _Italia_).               | Un objeto puede tener distintas dataciones debido a discrepancias históricas (por ejemplo, _siglos XVII–XVIII_).              |

## Instituciones participantes

Universitat de València (UV):

- Instituto de Robótica y Tecnologías de la Información y la Comunicación (IRTIC)
- Departamento de Historia del Arte

## Financiación y colaboración institucional

Financiado por el Ministerio de Ciencia e Innovación de España a través de la convocatoria de **Proyectos de Generación de Conocimiento 2021**.

El proyecto también ha contado con la colaboración de la **Subdirección General de Museos Estatales**, organismo del Ministerio de Cultura, que ha facilitado el acceso y utilización de los datos patrimoniales empleados en la plataforma.

## Fuente de datos

- CER.es (Colecciones en Red de Museos de España): https://ceres.mcu.es

**Disponibilidad de los datos:** Debido a las restricciones establecidas en el convenio de colaboración entre la Universitat de València (UV) y el Ministerio de Cultura y Deporte (MCD), los datos en bruto no pueden distribuirse públicamente. No obstante, la información puede consultarse públicamente a través de la plataforma CER.es.

## Resultados

El proyecto ha dado lugar a diversos desarrollos experimentales relacionados con la visualización espacial y temporal de datos patrimoniales. Parte de estos resultados se encuentran disponibles en los siguientes repositorios y visualizaciones:

| Proyecto                  | Categoría              | Visualización / Recurso    | Enlace                                                                                                       |
| ------------------------- | ---------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **CIMED**                 | Provenancia geográfica | Hexbin GeoNames Provenance | [Ver](https://dinaresearchteam.github.io/CIMED/assets/visualizations/hex_geonames_provenance.html)           |
|                           |                        | Mapa GeoNames Provenance   | [Ver](https://dinaresearchteam.github.io/CIMED/assets/visualizations/map_geonames_provenance.html)           |
|                           | Numismática            | Períodos de Numismática    | [Ver](https://dinaresearchteam.github.io/CIMED/assets/visualizations/periodos_numismatica.html)              |
|                           | Tendencias Sorolla     | Tendencia Sorolla          | [Ver](https://dinaresearchteam.github.io/CIMED/assets/visualizations/tendencia_sorolla1.html)                |
|                           |                        | Heatmap Tipos Sorolla      | [Ver](https://dinaresearchteam.github.io/CIMED/assets/visualizations/tendencia_sorolla_tipos_heatmap.html)   |
| **ICP Visualizations**    | Visualización          | ICP-Visualizations         | [Ver](https://dinaresearchteam.github.io/ICP-Visualizations/)                                                |
| **Temporal Idiosyncrasy** | Temporalidad           | Temporal-Idiosyncrasy      | [Ver](https://dinaresearchteam.github.io/Temporal-Idiosyncrasy/)                                             |
| **API Geocoding**         | Comparativa APIs       | Hex Differences ArcGIS     | [Ver](https://dinaresearchteam.github.io/API-Geocoding/assets/visualizations/hex_differences_ArcGIS.html)    |
|                           |                        | Hex Differences GeoNames   | [Ver](https://dinaresearchteam.github.io/API-Geocoding/assets/visualizations/hex_differences_GeoNames.html)  |
|                           |                        | Hex Differences Nominatim  | [Ver](https://dinaresearchteam.github.io/API-Geocoding/assets/visualizations/hex_differences_Nominatim.html) |
|                           | Provenancia            | Mapa GeoNames Provenance   | [Ver](https://dinaresearchteam.github.io/API-Geocoding/assets/visualizations/map_geonames_provenance.html)   |

## Código creado

El código desarrollado para las distintas visualizaciones y experimentos del proyecto se encuentra disponible en el siguiente repositorio: [Visualizaciones](./codigo/)

## Tecnologías utilizadas

Este proyecto combina herramientas de análisis de datos, visualización interactiva y desarrollo web para el procesamiento y exploración de información geoespacial.

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

![Pandas](https://img.shields.io/badge/Pandas-2C2D72?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/Numpy-777BB4?style=for-the-badge&logo=numpy&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-000000?style=for-the-badge&logo=python&logoColor=white)
![Seaborn](https://img.shields.io/badge/Seaborn-4C72B0?style=for-the-badge&logo=python&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-239120?style=for-the-badge&logo=plotly&logoColor=white)
![Folium](https://img.shields.io/badge/Folium-77B829?style=for-the-badge&logo=folium&logoColor=white)
![GeoPandas](https://img.shields.io/badge/GeoPandas-139C5A?style=for-the-badge&logo=python&logoColor=white)
![Shapely](https://img.shields.io/badge/Shapely-5C2D91?style=for-the-badge&logo=python&logoColor=white)
![GeoJSON](https://img.shields.io/badge/GeoJSON-000000?style=for-the-badge&logo=python&logoColor=white)

![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green)
![JavaScript](https://img.shields.io/badge/JavaScript-323330?style=for-the-badge&logo=javascript&logoColor=F7DF1E)
