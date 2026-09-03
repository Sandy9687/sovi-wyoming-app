# Wyoming Social Vulnerability Index (SoVI) Explorer

An interactive web application for exploring Social Vulnerability Index (SoVI) results across Wyoming, built as part of a Master's thesis investigating the geography of social vulnerability and wildfire risk in Wyoming (Geographic Information Science and Technology / Environment and Natural Resources, University of Wyoming).

**Live app:** [https://sovi-wyoming-app-brfyj4nwsc5appfyczfxkmh.streamlit.app/](https://sovi-wyoming-app-brfyj4nwsc5appfyczfxkmh.streamlit.app/)

## Overview

The Social Vulnerability Index (SoVI), following the methodology developed by Cutter, Boruff, and Shirley (2003) and updated by Cutter & Emrich (2017), is an empirically-based measure of the socioeconomic and demographic factors that shape a community's ability to prepare for, respond to, and recover from hazards. This app lets users explore SoVI results for Wyoming at both the **tract** and **county** level, across several alternative model configurations, and see where high- and low-vulnerability areas cluster spatially.

## Features

- **Interactive choropleth maps** of SoVI scores, standard-deviation classes, and Local Indicators of Spatial Association (LISA) clusters
- **Multiple geography levels**: Census tract and county
- **Multiple model configurations**, each built from a distinct Principal Component Analysis (PCA):
  - **All Variables Method** — full available variable set
  - **Predicted Variables Removed** *(tract-level only)* — excludes modeled/proxy variables, retaining only directly measured ACS variables
  - **Urban Region Vulnerability** — excludes agriculture-dependence variables
  - **Rural Region Vulnerability** — excludes urban-density variables
- **Underlying data table** for each unit (tract or county), including SoVI score, class, and LISA cluster designation
- **Variable list** showing exactly which input variables fed into each model's PCA

## Methodology

Each configuration follows the same pipeline:

1. Variable selection and z-score standardization (mean 0, SD 1)
2. Correlation-based pruning (iteratively removing one variable from any pair correlated above |r| = 0.85)
3. Kaiser-Meyer-Olkin (KMO) sampling adequacy and Bartlett's test of sphericity
4. Principal Component Analysis with varimax rotation, retaining components with eigenvalue > 1 (Kaiser criterion)
5. Component naming and cardinality assignment (whether a component increases or decreases vulnerability), informed by the original Cutter & Emrich framework and adapted for Wyoming's socioeconomic context
6. SoVI score computed as the cardinality-weighted sum of component scores
7. Spatial analysis via Global and Local Moran's I to identify significant clusters

County-level models were computed across all 281 counties of the Mountain Census Division (Arizona, Colorado, Idaho, Montana, Nevada, New Mexico, Utah, Wyoming) to provide adequate statistical power for PCA, then filtered to Wyoming's 23 counties for display — consistent with standard SoVI practice for states with too few counties to meet minimum sample-size requirements on their own.

## Data Sources

- U.S. Census Bureau, American Community Survey (5-Year Estimates, 2020–2024)
- U.S. Census Bureau, 2020 Decennial Census
- U.S. Bureau of Economic Analysis (BEA), Regional Economic Accounts
- USDA National Agricultural Statistics Service (NASS), Census of Agriculture
- HRSA Area Health Resources Files (AHRF)
- HIFLD Open Data, Hospitals
- Social Security Administration, OASDI Beneficiaries by County
- MIT Election Lab, County Presidential Election Returns
- Census of Governments, Annual Survey of State and Local Government Finances

## Repository Structure

```
sovi-wyoming-app/
├── app.py              # Streamlit application
├── requirements.txt     # Python dependencies
└── data/                 # GeoJSON files (one per geography × configuration)
    ├── tract_all_vars.geojson
    ├── tract_predvars_removed.geojson
    ├── tract_urban.geojson
    ├── tract_rural.geojson
    ├── county_all_vars.geojson
    ├── county_urban.geojson
    └── county_rural.geojson
```

## Running Locally

```bash
git clone https://github.com/Sandy9687/sovi-wyoming-app.git
cd sovi-wyoming-app
pip install -r requirements.txt
streamlit run app.py
```

## Author

Sandip Pantha
M.S. Student, Geographic Information Science and Technology & Environment and Natural Resources
University of Wyoming

## Advisor

Dr. Jason "Jake" Hawes
Assistant Professor
School of Computing, Haub School of Environment and Natural Resources
University of Wyoming

## Acknowledgments

SoVI methodology adapted from Cutter, S. L., Boruff, B. J., & Shirley, W. L. (2003). *Social vulnerability to environmental hazards.* Social Science Quarterly, 84(2), 242–261, and Cutter, S. L. & Emrich, C. T. (2017). *Social Vulnerability Index (SoVI®): Methodology and Limitations.* Hazards & Vulnerability Research Institute, University of South Carolina.
