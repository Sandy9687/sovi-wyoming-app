import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Wyoming Social Vulnerability Index (SoVI)",
    layout="wide"
)

st.title("Wyoming Social Vulnerability Index (SoVI) Explorer")
st.markdown(
    "Interactive viewer for tract- and county-level Social Vulnerability Index "
    "results, comparing a reduced (few-variable) model against the "
    "All Variables Method."
)

# ==========================================
# DATA LOADING (cached so files aren't re-read on every interaction)
# ==========================================
DATA_DIR = "data/"

FILE_MAP = {
    ("Tract", "Few Variables"):        DATA_DIR + "tract_few_vars.geojson",
    ("Tract", "All Variables Method"): DATA_DIR + "tract_all_vars.geojson",
    ("County", "Few Variables"):       DATA_DIR + "county_few_vars.geojson",
    ("County", "All Variables Method"): DATA_DIR + "county_all_vars.geojson",
    ("County", "Urban Region Vulnerability"): DATA_DIR + "county_urban.geojson",
    ("County", "Rural Region Vulnerability"): DATA_DIR + "county_rural.geojson",
}

# Which "Variable Configuration" options are valid for each geography level.
GEOGRAPHY_CONFIGS = {
    "Tract":  ["Few Variables", "All Variables Method"],
    "County": ["Few Variables", "All Variables Method", "Urban Region Vulnerability", "Rural Region Vulnerability"],
}

# Columns that are identifiers, geometry, or computed OUTPUTS rather than
# input variables that went into the PCA/SoVI calculation. Everything else
# in a GeoJSON's columns is treated as an input variable for the variable list.
NON_INPUT_COLS = {
    "GISJOIN", "NAME", "NAME_E", "NAMELSAD", "COUNTY", "STATEFP", "COUNTYFP",
    "TRACTCE", "GEOID", "GEOIDFQ", "MTFCC", "FUNCSTAT", "ALAND", "AWATER",
    "INTPTLAT", "INTPTLON", "Area_miles", "geometry",
    "SoVI", "SoVI_class", "cluster", "Ii", "P.Ii", "lag_sovi",
}
NON_INPUT_COLS |= {f"FAC_{i}" for i in range(1, 15)}
NON_INPUT_COLS |= {f"RC{i}" for i in range(1, 15)}

# Human-readable labels for known abbreviated variable codes.
# Any column not in this dict is shown using its raw column name as a fallback.
VARIABLE_LABELS = {
    "ESL_PCT": "% Limited English proficiency",
    "MED_AGE": "Median age",
    "AGE_DEP": "Age dependency ratio",
    "Q_MINOR": "% Minority population",
    "AVG_HH_SZ": "Average household size",
    "Q_RENTER": "% Renter-occupied housing",
    "Q_MOBILE": "% Mobile homes",
    "HOSP_PC": "Hospitals per capita",
    "Q_UNEMP": "% Unemployed",
    "Q_EXTRACT": "% Employment in extractive industries",
    "Q_TRANS": "Commute time / transport burden",
    "Q_SERV": "% Employment in service occupations",
    "FEM_LBR": "% Females in labor force",
    "LBR_FORCE": "% Total labor force participation",
    "POP_CHG": "Population change",
    "HOU_DEN": "Housing unit density",
    "NO_HS": "% Without high school education",
    "Q_FHH": "% Female-headed households",
    "Q_GRP_QTR": "% In group quarters",
    "Q_POV": "% In poverty",
    "Q_FEMALE": "% Female population",
    "HLTH_INS": "% With health insurance",
    "NO_VEH": "% Households with no vehicle",
    "PERCAP": "Per capita income",
    "HH_ABV_MED": "% Households above median income",
    "MED_VAL": "Median home value",
    "MED_RENT": "Median gross rent",
    "PCT_URBAN": "% Urban population",
    "PRED_BRATE": "Birth rate",
    "PRED_PCT_GOP": "% Voting for governing party",
    "PRED_MFG_DEN": "Manufacturing density",
    "PRED_SS_PC": "Social Security recipients per capita",
    "PRED_DEBT_RATIO": "Municipal debt ratio",
    "PRED_DEBT_REV": "Municipal debt-to-revenue ratio",
    "PRED_PERMIT_DEN": "Housing permit density",
    "PRED_NURS_PC": "Nurses per capita",
    "PRED_PHYS_PC": "Physicians per capita",
    "PRED_GDP_PC": "GDP per capita",
    "PRED_COM_DEN": "Commercial density",
    "PRED_PCT_FARM": "% In farming",
    "PRED_FARM_VAL": "Farm production value",
    # County-level Mountain Division variables (directly measured, not modeled -
    # no PRED_ prefix, since these come straight from BEA/USDA/HRSA/SSA/Census sources)
    "PCT_GOP": "% Voting for governing party",
    "SS_PC": "Social Security recipients per capita",
    "DEBT_RATIO": "Municipal debt ratio (liabilities/assets)",
    "GDP_PC": "GDP per capita",
    "PCT_FARM": "% Land in farms",
    "FARM_VAL": "Farm production & land value per sq. mile",
    "NURS_PC": "% Population in nursing facilities",
    "PHYS_PC": "Physicians per 100,000 population",
}

@st.cache_data
def load_geojson(path):
    gdf = gpd.read_file(path)
    # Ensure WGS84 for web mapping
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf

def get_input_variables(gdf):
    """Return the list of input variable column names used for this configuration."""
    cols = [c for c in gdf.columns if c not in NON_INPUT_COLS]
    return sorted(cols)

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Configuration")

geography = st.sidebar.selectbox("Geography Level", ["Tract", "County"])
variable_set = st.sidebar.selectbox("Variable Configuration", GEOGRAPHY_CONFIGS[geography])

output_view = st.sidebar.selectbox(
    "Output View",
    ["SoVI Score", "SoVI Class", "LISA Cluster"],
    index=0  # SoVI Score front-and-center by default
)

# ==========================================
# LOAD SELECTED DATA
# ==========================================
selected_path = FILE_MAP[(geography, variable_set)]

try:
    gdf = load_geojson(selected_path)
except Exception as e:
    st.error(f"Could not load {selected_path}. Make sure your GeoJSON files "
             f"are in the 'data/' folder next to this app.py. Error: {e}")
    st.stop()

# Use NAME field for hover label
name_field = "NAME" if "NAME" in gdf.columns else gdf.columns[0]

# ==========================================
# MAP RENDERING BASED ON SELECTED OUTPUT
# ==========================================
st.subheader(f"{geography}-Level {output_view} ({variable_set})")

col_map, col_table = st.columns([2, 1])

with col_map:
    if output_view == "SoVI Score":
        fig = px.choropleth_mapbox(
            gdf,
            geojson=gdf.geometry.__geo_interface__,
            locations=gdf.index,
            color="SoVI",
            color_continuous_scale="RdYlGn_r",
            mapbox_style="carto-positron",
            center={"lat": 43.0, "lon": -107.5},
            zoom=5.3,
            opacity=0.75,
            hover_name=name_field,
            hover_data={"SoVI": True, "SoVI_class": True},
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=650)
        st.plotly_chart(fig, use_container_width=True)

    elif output_view == "SoVI Class":
        fig = px.choropleth_mapbox(
            gdf,
            geojson=gdf.geometry.__geo_interface__,
            locations=gdf.index,
            color="SoVI_class",
            category_orders={"SoVI_class": ["< -1 SD", "-1 to -0.5 SD", "-0.5 to 0.5 SD", "0.5 to 1 SD", "> 1 SD"]},
            color_discrete_sequence=px.colors.diverging.RdYlGn[::-1],
            mapbox_style="carto-positron",
            center={"lat": 43.0, "lon": -107.5},
            zoom=5.3,
            opacity=0.75,
            hover_name=name_field,
            hover_data={"SoVI": True, "SoVI_class": True},
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=650)
        st.plotly_chart(fig, use_container_width=True)

    elif output_view == "LISA Cluster":
        cluster_colors = {
            "High-High": "#d73027",
            "Low-Low": "#4575b4",
            "High-Low": "#fee090",
            "Low-High": "#91bfdb",
            "Not Significant": "#cccccc",
        }
        fig = px.choropleth_mapbox(
            gdf,
            geojson=gdf.geometry.__geo_interface__,
            locations=gdf.index,
            color="cluster",
            category_orders={"cluster": list(cluster_colors.keys())},
            color_discrete_map=cluster_colors,
            mapbox_style="carto-positron",
            center={"lat": 43.0, "lon": -107.5},
            zoom=5.3,
            opacity=0.75,
            hover_name=name_field,
            hover_data={"SoVI": True, "cluster": True},
        )
        fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=650)
        st.plotly_chart(fig, use_container_width=True)

with col_table:
    st.markdown("**Underlying Data**")
    display_cols = [c for c in [name_field, "SoVI", "SoVI_class", "cluster", "Ii", "P.Ii"] if c in gdf.columns]
    table_df = gdf[display_cols].sort_values("SoVI", ascending=False).reset_index(drop=True)
    st.dataframe(table_df, use_container_width=True, height=650)

# ==========================================
# VARIABLES USED IN THIS CONFIGURATION
# ==========================================
input_vars = get_input_variables(gdf)

with st.expander(f"Variables used in the {variable_set} model ({len(input_vars)} variables)", expanded=False):
    var_rows = [
        {"Variable Code": v, "Description": VARIABLE_LABELS.get(v, "—")}
        for v in input_vars
    ]
    st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)

# ==========================================
# SUMMARY STATS
# ==========================================
st.markdown("---")
st.subheader("Summary Statistics")

s1, s2, s3, s4 = st.columns(4)
s1.metric("Number of Units", len(gdf))
s2.metric("Mean SoVI", round(gdf["SoVI"].mean(), 3))
s3.metric("Min SoVI", round(gdf["SoVI"].min(), 3))
s4.metric("Max SoVI", round(gdf["SoVI"].max(), 3))

if "SoVI_class" in gdf.columns:
    st.markdown("**Counts by SoVI Class**")
    class_counts = gdf["SoVI_class"].value_counts().reindex(
        ["< -1 SD", "-1 to -0.5 SD", "-0.5 to 0.5 SD", "0.5 to 1 SD", "> 1 SD"]
    ).fillna(0).astype(int)
    st.bar_chart(class_counts)

st.markdown("---")
if geography == "County" and variable_set != "Few Variables":
    st.caption(
        "County-level PCA was computed across all 281 counties of the Mountain "
        "Census Division (AZ, CO, ID, MT, NV, NM, UT, WY) to provide adequate "
        "statistical power, then filtered to Wyoming's 23 counties for display, "
        "consistent with standard SoVI methodology for small states."
    )
st.caption(
    "Data: Wyoming SoVI analysis, tract and county level, few- and "
    "all-variable model configurations. Local Moran's I (LISA) used to "
    "identify spatial clusters and outliers."
)
