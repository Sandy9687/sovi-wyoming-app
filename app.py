import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

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
    "results across multiple model configurations: All Variables, Urban Region "
    "Vulnerability, Rural Region Vulnerability, and (tract-level only) Predicted "
    "Variables Removed."
)

# ==========================================
# DATA LOADING (cached so files aren't re-read on every interaction)
# ==========================================
DATA_DIR = "data/"

FILE_MAP = {
    ("Tract", "All Variables Method"): DATA_DIR + "tract_all_vars.geojson",
    ("Tract", "Predicted Variables Removed"): DATA_DIR + "tract_predvars_removed.geojson",
    ("Tract", "Urban Region Vulnerability"): DATA_DIR + "tract_urban.geojson",
    ("Tract", "Rural Region Vulnerability"): DATA_DIR + "tract_rural.geojson",
    ("County", "All Variables Method"): DATA_DIR + "county_all_vars.geojson",
    ("County", "Urban Region Vulnerability"): DATA_DIR + "county_urban.geojson",
    ("County", "Rural Region Vulnerability"): DATA_DIR + "county_rural.geojson",
}

# Which "Variable Configuration" options are valid for each geography level.
GEOGRAPHY_CONFIGS = {
    "Tract":  ["All Variables Method", "Predicted Variables Removed",
               "Urban Region Vulnerability", "Rural Region Vulnerability"],
    "County": ["All Variables Method", "Urban Region Vulnerability", "Rural Region Vulnerability"],
}

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
    # Comparison variables (from FEMA National Risk Index) - not PCA inputs,
    # attached separately for benchmarking against your SoVI results
    "WFIR_RISKS": "Wildfire Risk Score (FEMA NRI)",
    "SOVI_SCORE": "Social Vulnerability Score (FEMA / CDC-ATSDR)",
}

# Comparison variables available on top of the PCA-input variables, once the
# wildfire/FEMA-SVI comparison data has been attached to a GeoJSON.
COMPARISON_VARS = ["WFIR_RISKS", "SOVI_SCORE"]

# ------------------------------------------
# Hardcoded variable lists per configuration. This is more reliable than
# deriving from GeoJSON columns, since the exported files only carry the
# final PCA component scores and SoVI outputs, not the raw input variables.
# ------------------------------------------
CONFIG_VARIABLES = {
    ("Tract", "All Variables Method"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_EXTRACT", "Q_TRANS", "Q_SERV", "FEM_LBR", "LBR_FORCE",
        "POP_CHG", "HOU_DEN", "NO_HS", "Q_GRP_QTR", "Q_POV", "Q_FEMALE", "HLTH_INS",
        "NO_VEH", "PERCAP", "MED_VAL", "MED_RENT", "PCT_URBAN", "PRED_BRATE",
        "PRED_PCT_GOP", "PRED_SS_PC", "PRED_NURS_PC", "PRED_PHYS_PC", "PRED_GDP_PC",
        "PRED_FARM_VAL",
    ],
    ("Tract", "Predicted Variables Removed"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_EXTRACT", "Q_TRANS", "Q_SERV", "FEM_LBR", "LBR_FORCE",
        "POP_CHG", "HOU_DEN", "NO_HS", "Q_FHH", "Q_GRP_QTR", "Q_POV", "Q_FEMALE",
        "HLTH_INS", "NO_VEH", "PERCAP", "MED_VAL", "MED_RENT", "PCT_URBAN",
    ],
    ("Tract", "Urban Region Vulnerability"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_TRANS", "Q_SERV", "FEM_LBR", "LBR_FORCE", "POP_CHG",
        "HOU_DEN", "NO_HS", "Q_GRP_QTR", "Q_POV", "Q_FEMALE", "HLTH_INS", "NO_VEH",
        "PERCAP", "MED_VAL", "MED_RENT", "PCT_URBAN", "PRED_BRATE", "PRED_PCT_GOP",
        "PRED_SS_PC", "PRED_NURS_PC", "PRED_PHYS_PC", "PRED_GDP_PC",
    ],
    ("Tract", "Rural Region Vulnerability"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_EXTRACT", "Q_TRANS", "FEM_LBR", "LBR_FORCE", "POP_CHG",
        "NO_HS", "Q_GRP_QTR", "Q_POV", "Q_FEMALE", "HLTH_INS", "NO_VEH", "PERCAP",
        "MED_VAL", "MED_RENT", "PRED_BRATE", "PRED_PCT_GOP", "PRED_SS_PC",
        "PRED_NURS_PC", "PRED_PHYS_PC", "PRED_PCT_FARM", "PRED_FARM_VAL",
    ],
    ("County", "All Variables Method"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_EXTRACT", "Q_TRANS", "Q_SERV", "FEM_LBR", "LBR_FORCE",
        "POP_CHG", "HOU_DEN", "NO_HS", "Q_FHH", "Q_GRP_QTR", "Q_POV", "Q_FEMALE",
        "HLTH_INS", "NO_VEH", "PERCAP", "HH_ABV_MED", "MED_VAL", "MED_RENT",
        "PCT_URBAN", "PCT_GOP", "SS_PC", "DEBT_RATIO", "GDP_PC", "PCT_FARM",
        "FARM_VAL", "NURS_PC", "PHYS_PC",
    ],
    ("County", "Urban Region Vulnerability"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_TRANS", "Q_SERV", "FEM_LBR", "LBR_FORCE", "POP_CHG",
        "HOU_DEN", "NO_HS", "Q_FHH", "Q_GRP_QTR", "Q_POV", "Q_FEMALE", "HLTH_INS",
        "NO_VEH", "PERCAP", "HH_ABV_MED", "MED_VAL", "MED_RENT", "PCT_URBAN",
        "PCT_GOP", "SS_PC", "DEBT_RATIO", "GDP_PC", "NURS_PC", "PHYS_PC",
    ],
    ("County", "Rural Region Vulnerability"): [
        "ESL_PCT", "MED_AGE", "AGE_DEP", "Q_MINOR", "AVG_HH_SZ", "Q_RENTER", "Q_MOBILE",
        "HOSP_PC", "Q_UNEMP", "Q_EXTRACT", "Q_TRANS", "FEM_LBR", "LBR_FORCE", "POP_CHG",
        "NO_HS", "Q_FHH", "Q_GRP_QTR", "Q_POV", "Q_FEMALE", "HLTH_INS", "NO_VEH",
        "PERCAP", "HH_ABV_MED", "MED_VAL", "MED_RENT", "PCT_GOP", "SS_PC",
        "DEBT_RATIO", "GDP_PC", "PCT_FARM", "FARM_VAL", "NURS_PC", "PHYS_PC",
    ],
}

@st.cache_data
def load_geojson(path):
    gdf = gpd.read_file(path)
    # Ensure WGS84 for web mapping
    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf

@st.cache_data
def gdf_to_geojson_str(path, _gdf):
    """Cache the expensive GeoDataFrame -> GeoJSON string conversion.
    Keyed on file path so it's computed once per file, not once per rerun."""
    return _gdf.reset_index().to_json()

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
            mapbox_style="open-street-map",
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
            mapbox_style="open-street-map",
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
            mapbox_style="open-street-map",
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
input_vars = CONFIG_VARIABLES.get((geography, variable_set), [])

with st.expander(f"Variables used in the {variable_set} model ({len(input_vars)} variables)", expanded=False):
    var_rows = [
        {"Variable Code": v, "Description": VARIABLE_LABELS.get(v, "—")}
        for v in input_vars
    ]
    st.dataframe(pd.DataFrame(var_rows), use_container_width=True, hide_index=True)

# ==========================================
# INDIVIDUAL VARIABLE EXPLORER
# Lets the user pick any single input variable and see its raw values,
# either alone or layered on top of the SoVI choropleth with a toggle.
# ==========================================
st.markdown("---")
st.subheader("Individual Variable Explorer")
st.markdown(
    f"Explore any single variable's raw values by tract/county, and optionally "
    f"overlay it on top of the currently selected **{output_view}** map (chosen "
    f"in the Output View dropdown above) to see how that variable relates to "
    f"vulnerability. Use the layer control (top right of the map) to toggle "
    f"each layer on or off."
)

available_vars = [v for v in input_vars + COMPARISON_VARS if v in gdf.columns]
missing_vars = [v for v in input_vars if v not in gdf.columns]

if missing_vars:
    st.info(
        f"{len(missing_vars)} of {len(input_vars)} variables aren't in this file yet "
        f"(raw values need to be re-exported from R — see the app's data pipeline). "
        f"Showing the {len(available_vars)} that are available."
    )

if not available_vars:
    st.warning(
        "No raw variable values are available in this GeoJSON yet. "
        "Re-export the data from R with the original variable columns included "
        "to enable this feature."
    )
else:
    selected_var = st.selectbox(
        "Select a variable to explore",
        available_vars,
        format_func=lambda v: f"{VARIABLE_LABELS.get(v, v)} ({v})"
    )

    show_sovi_layer = st.checkbox(f"Show {output_view} layer", value=True)
    show_var_layer = st.checkbox(f"Show {VARIABLE_LABELS.get(selected_var, selected_var)} layer", value=True)

    load_explorer_map = True  # automatic rendering (no button gate)

    if load_explorer_map:
        # Build a Folium map with genuinely toggleable layers via LayerControl
        center_lat, center_lon = 43.0, -107.5
        m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles="OpenStreetMap")

        gdf_json = gdf_to_geojson_str(selected_path, gdf)

        # --- Base layer: follows whichever Output View is currently selected above ---
        if show_sovi_layer:
            if output_view == "SoVI Score":
                base_colormap = cm.LinearColormap(
                    colors=["#1a9850", "#ffffbf", "#d73027"],  # green (low) -> yellow -> red (high)
                    vmin=gdf["SoVI"].min(),
                    vmax=gdf["SoVI"].max(),
                    caption="SoVI Score"
                )
                style_fn = lambda feature, cmap=base_colormap: {
                    "fillColor": cmap(feature["properties"]["SoVI"]),
                    "color": "black", "weight": 0.5, "fillOpacity": 0.75,
                }
                base_layer_name = "SoVI Score"

            elif output_view == "SoVI Class":
                class_colors = {
                    "< -1 SD": "#1a9850", "-1 to -0.5 SD": "#a6d96a", "-0.5 to 0.5 SD": "#ffffbf",
                    "0.5 to 1 SD": "#fdae61", "> 1 SD": "#d73027",
                }
                style_fn = lambda feature: {
                    "fillColor": class_colors.get(feature["properties"].get("SoVI_class"), "#cccccc"),
                    "color": "black", "weight": 0.5, "fillOpacity": 0.75,
                }
                base_layer_name = "SoVI Class"

            else:  # LISA Cluster
                cluster_colors = {
                    "High-High": "#d73027", "Low-Low": "#4575b4", "High-Low": "#fee090",
                    "Low-High": "#91bfdb", "Not Significant": "#cccccc",
                }
                style_fn = lambda feature: {
                    "fillColor": cluster_colors.get(feature["properties"].get("cluster"), "#cccccc"),
                    "color": "black", "weight": 0.5, "fillOpacity": 0.75,
                }
                base_layer_name = "LISA Cluster"

            folium.GeoJson(
                gdf_json,
                name=base_layer_name,
                style_function=style_fn,
                tooltip=folium.GeoJsonTooltip(
                    fields=[f for f in [name_field, "SoVI", "SoVI_class", "cluster"] if f in gdf.columns],
                    aliases=[a for f, a in zip(
                        [name_field, "SoVI", "SoVI_class", "cluster"],
                        ["Name:", "SoVI Score:", "SoVI Class:", "LISA Cluster:"]
                    ) if f in gdf.columns],
                    localize=True,
                ),
                show=True,
            ).add_to(m)

            if output_view == "SoVI Score":
                base_colormap.add_to(m)

        # --- Individual variable layer (lighter color scale, so it reads as a secondary layer) ---
        # Color scale always uses the NORMALIZED value (for consistent comparison across
        # variables); tooltip shows the REAL, pre-normalization value when available, so
        # people see an interpretable number rather than a z-score.
        raw_col = f"{selected_var}_RAW"
        has_raw = raw_col in gdf.columns

        if show_var_layer:
            var_colormap = cm.LinearColormap(
                colors=["#f7fbff", "#6baed6", "#08306b"],  # light blue (low) -> dark blue (high), lighter overall than SoVI's red/green
                vmin=gdf[selected_var].min(),
                vmax=gdf[selected_var].max(),
                caption=VARIABLE_LABELS.get(selected_var, selected_var)
            )

            tooltip_fields = [name_field, raw_col if has_raw else selected_var, "SoVI"]
            tooltip_aliases = [
                "Name:",
                f"{VARIABLE_LABELS.get(selected_var, selected_var)} (actual value):" if has_raw
                    else f"{VARIABLE_LABELS.get(selected_var, selected_var)} (normalized):",
                "SoVI Score:"
            ]

            folium.GeoJson(
                gdf_json,
                name=f"{VARIABLE_LABELS.get(selected_var, selected_var)} ({selected_var})",
                style_function=lambda feature, cmap=var_colormap, var=selected_var: {
                    "fillColor": cmap(feature["properties"][var]),
                    "color": "#555555",
                    "weight": 0.5,
                    "fillOpacity": 0.55,  # lighter/more transparent than the SoVI layer
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=tooltip_fields,
                    aliases=tooltip_aliases,
                    localize=True,
                ),
                show=True,
            ).add_to(m)
            var_colormap.add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)

        st_folium(m, use_container_width=True, height=600, key="explorer_map")

        # Quick summary of the selected variable alongside SoVI, for direct comparison
        # Shows the REAL (pre-normalization) value when available, so the numbers are
        # directly interpretable rather than z-scores.
        display_var = raw_col if has_raw else selected_var
        display_label = f"{VARIABLE_LABELS.get(selected_var, selected_var)}" + (" (actual value)" if has_raw else " (normalized)")

        st.markdown(f"**{display_label} vs. SoVI — top 10 tracts/counties by this variable**")
        compare_cols = [c for c in [name_field, display_var, "SoVI", "SoVI_class"] if c in gdf.columns]
        table_df = gdf[compare_cols].sort_values(display_var, ascending=False).head(10).reset_index(drop=True)
        table_df = table_df.rename(columns={display_var: display_label})
        st.dataframe(
            table_df,
            use_container_width=True, hide_index=True
        )

# ==========================================
# WILDFIRE RISK & FEMA SVI COMPARISON
# Benchmarks this SoVI configuration against FEMA's National Risk Index
# wildfire risk score and its CDC/ATSDR-based social vulnerability score.
# ==========================================
st.markdown("---")
st.subheader("Wildfire Risk & FEMA SVI Comparison")

if "WFIR_RISKS" not in gdf.columns or "SOVI_SCORE" not in gdf.columns:
    st.warning(
        "Wildfire risk and FEMA SVI comparison data aren't attached to this "
        "configuration's file yet. Re-export from R with the FEMA NRI join "
        "to enable this section."
    )
else:
    st.markdown(
        "Comparing this model's SoVI score against FEMA's National Risk Index (NRI) "
        "**wildfire risk score** and its own **social vulnerability score** "
        "(based on the CDC/ATSDR methodology), for the same tracts/counties."
    )

    # Live correlation stats (computed from the currently loaded data)
    valid = gdf.dropna(subset=["SoVI", "WFIR_RISKS", "SOVI_SCORE"])
    corr_wildfire = valid["SoVI"].corr(valid["WFIR_RISKS"])
    corr_fema_svi = valid["SoVI"].corr(valid["SOVI_SCORE"])

    c1, c2 = st.columns(2)
    c1.metric("Correlation: Your SoVI vs. Wildfire Risk", round(corr_wildfire, 3))
    c2.metric("Correlation: Your SoVI vs. FEMA/CDC-ATSDR SVI", round(corr_fema_svi, 3))

    # Quadrant map (High/Low Vulnerability x High/Low Wildfire Risk)
    if "quadrant" in gdf.columns:
        quadrant_colors = {
            "High Vulnerability & High Wildfire Risk": "#d73027",
            "High Vulnerability & Low Wildfire Risk": "#fee090",
            "Low Vulnerability & High Wildfire Risk": "#91bfdb",
            "Low Vulnerability & Low Wildfire Risk": "#4575b4",
        }

        m_quad = folium.Map(location=[43.0, -107.5], zoom_start=7, tiles="OpenStreetMap")
        gdf_json_quad = gdf_to_geojson_str(selected_path, gdf)

        folium.GeoJson(
            gdf_json_quad,
            name="Vulnerability-Wildfire Quadrant",
            style_function=lambda feature: {
                "fillColor": quadrant_colors.get(feature["properties"].get("quadrant"), "#cccccc"),
                "color": "black", "weight": 0.5, "fillOpacity": 0.75,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=[f for f in [name_field, "SoVI", "WFIR_RISKS", "SOVI_SCORE", "quadrant"] if f in gdf.columns],
                aliases=["Name:", "Your SoVI:", "Wildfire Risk:", "FEMA SVI:", "Quadrant:"],
                localize=True,
            ),
        ).add_to(m_quad)

        # Simple legend
        legend_html = """
        <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                    background: white; padding: 10px; border: 1px solid #999; font-size: 13px;">
        <b>Quadrant</b><br>
        <span style="color:#d73027;">&#9632;</span> High Vulnerability & High Wildfire Risk<br>
        <span style="color:#fee090;">&#9632;</span> High Vulnerability & Low Wildfire Risk<br>
        <span style="color:#91bfdb;">&#9632;</span> Low Vulnerability & High Wildfire Risk<br>
        <span style="color:#4575b4;">&#9632;</span> Low Vulnerability & Low Wildfire Risk
        </div>
        """
        m_quad.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m_quad, use_container_width=True, height=550, key="quadrant_map")

        # Quadrant breakdown table
        quad_counts = gdf["quadrant"].value_counts().reset_index()
        quad_counts.columns = ["Quadrant", "Count"]
        quad_counts["Percent"] = round(100 * quad_counts["Count"] / quad_counts["Count"].sum(), 1)
        st.dataframe(quad_counts, use_container_width=True, hide_index=True)

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
