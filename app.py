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
    "results, comparing a reduced (few-variable) model against a full "
    "(all-variable) model."
)

# ==========================================
# DATA LOADING (cached so files aren't re-read on every interaction)
# ==========================================
DATA_DIR = "data/"

FILE_MAP = {
    ("Tract", "Few Variables"):  DATA_DIR + "tract_few_vars.geojson",
    ("Tract", "All Variables"):  DATA_DIR + "tract_all_vars.geojson",
    ("County", "Few Variables"): DATA_DIR + "county_few_vars.geojson",
    ("County", "All Variables"): DATA_DIR + "county_all_vars.geojson",
}

@st.cache_data
def load_geojson(path):
    gdf = gpd.read_file(path)
    # Ensure WGS84 for web mapping
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("Configuration")

geography = st.sidebar.selectbox("Geography Level", ["Tract", "County"])
variable_set = st.sidebar.selectbox("Variable Configuration", ["Few Variables", "All Variables"])

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
st.caption(
    "Data: Wyoming SoVI analysis, tract and county level, few- and "
    "all-variable model configurations. Local Moran's I (LISA) used to "
    "identify spatial clusters and outliers."
)
