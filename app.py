from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(
    page_title="AirSentinel",
    page_icon="🌍",
    layout="wide",
)

DATA_FILE = Path("data/processed/city_conditions.csv")
FORECAST_FILE = Path("data/processed/chennai_latest_forecast.csv")
MULTI_HORIZON_FORECAST_FILE = Path(
    "data/processed/chennai_multi_horizon_latest_forecast.csv"
)
RISK_FILE = Path("data/processed/city_risk_scores.csv")
LOCALITY_PROFILE_FILE = Path("data/processed/locality_evidence_profile.csv")
LOCALITY_FORECAST_FILE = Path(
    "data/processed/locality_multi_horizon_latest_forecast.csv"
)

if not DATA_FILE.exists():
    st.error("City conditions data is missing.")
    st.stop()

city_conditions = pd.read_csv(DATA_FILE)
risk_scores = None

active_cities = city_conditions.dropna(
    subset=["current_pm25"]
).copy()

st.title("🌍 AirSentinel — India Overview")
st.caption(
    "Source-labelled early-warning prototype using monitored PM2.5 and weather "
    "context. Fallback data is not official AQI or a live government alert."
)

highest_city = active_cities.loc[
    active_cities["current_pm25"].idxmax()
]

average_pm25 = active_cities["current_pm25"].mean()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Cities with fresh PM2.5 data",
    f"{len(active_cities)} / {len(city_conditions)}",
)

col2.metric(
    "Average current PM2.5",
    f"{average_pm25:.1f} μg/m³",
)

col3.metric(
    "Highest current PM2.5",
    f"{highest_city['current_pm25']:.1f} μg/m³",
    highest_city["city_name"],
)

if MULTI_HORIZON_FORECAST_FILE.exists():
    multi_horizon_forecast = pd.read_csv(MULTI_HORIZON_FORECAST_FILE)
    horizon_order = {"1h": 1, "3h": 3, "4h": 4}
    multi_horizon_forecast["horizon_order"] = multi_horizon_forecast["horizon"].map(
        horizon_order
    )
    multi_horizon_forecast = multi_horizon_forecast.sort_values("horizon_order")

    st.subheader("Chennai early-warning forecast")
    st.caption(
        "Historical validation of direct 1-, 3- and 4-hour forecasts. Ranges are "
        "empirical prototype uncertainty ranges, not live alerts or guarantees."
    )

    forecast_columns = st.columns(len(multi_horizon_forecast))
    for column, forecast_row in zip(
        forecast_columns, multi_horizon_forecast.itertuples(index=False)
    ):
        column.metric(
            f"Predicted PM2.5 in {forecast_row.horizon}",
            f"{forecast_row.predicted_pm25:.1f} μg/m³",
            f"Input: {forecast_row.current_pm25_input:.1f} μg/m³",
        )
        column.caption(
            "Historical actual: "
            f"{forecast_row.historical_actual_pm25:.1f} μg/m³ | "
            f"Range: {forecast_row.empirical_range_low:.1f}–"
            f"{forecast_row.empirical_range_high:.1f} μg/m³"
        )

    first_row = multi_horizon_forecast.iloc[0]
    st.caption(
        "Input time: "
        f"{pd.to_datetime(first_row['input_timestamp_utc']).strftime('%d %b %Y, %H:%M UTC')} "
        "| Prototype model selected by chronological validation."
    )

elif FORECAST_FILE.exists():
    forecast_data = pd.read_csv(FORECAST_FILE)
    latest_forecast = forecast_data.iloc[0]

    input_time = pd.to_datetime(latest_forecast["timestamp_utc"])
    forecast_time = pd.to_datetime(latest_forecast["forecast_for_utc"])
    current_input = latest_forecast["current_pm25_input"]
    predicted_pm25 = latest_forecast["predicted_pm25_next_1h"]
    actual_pm25 = latest_forecast["actual_pm25_if_available"]

    st.subheader("Chennai one-hour PM2.5 forecast")
    st.caption(
        "Prototype historical validation using the latest available "
        "model-ready Chennai data. This is not a real-time alert."
    )

    forecast_col1, forecast_col2, forecast_col3 = st.columns(3)

    forecast_col1.metric(
        "PM2.5 input",
        f"{current_input:.1f} μg/m³",
        "Latest model input",
    )

    forecast_col2.metric(
        "Predicted PM2.5 in one hour",
        f"{predicted_pm25:.1f} μg/m³",
        f"{predicted_pm25 - current_input:+.1f} μg/m³",
    )

    forecast_col3.metric(
        "Recorded PM2.5 for validation",
        f"{actual_pm25:.1f} μg/m³",
        f"Model error: {abs(predicted_pm25 - actual_pm25):.1f} μg/m³",
    )

    st.write(
        f"Input time: {input_time.strftime('%d %b %Y, %H:%M UTC')}  |  "
        f"Forecast time: {forecast_time.strftime('%d %b %Y, %H:%M UTC')}"
    )

if RISK_FILE.exists():
    risk_scores = pd.read_csv(RISK_FILE)
    scored_cities = risk_scores.dropna(subset=["city_risk_score"]).copy()
    highest_risk_city = scored_cities.loc[
        scored_cities["city_risk_score"].idxmax()
    ]

    st.subheader("Sustainability risk and action guidance")
    st.caption(
        "Transparent prototype score: current PM2.5 severity plus a small "
        "weather-persistence adjustment. It is not an official AQI or a "
        "proven pollution-source assessment."
    )

    risk_col1, risk_col2, risk_col3 = st.columns(3)

    risk_col1.metric(
        "Very high-risk cities",
        int((risk_scores["risk_level"] == "Very High").sum()),
    )

    risk_col2.metric(
        "Highest prototype risk score",
        f"{highest_risk_city['city_risk_score']:.0f} / 100",
        highest_risk_city["city_name"],
    )

    risk_col3.metric(
        "Cities with unavailable PM2.5",
        int((risk_scores["risk_level"] == "Data unavailable").sum()),
    )

    risk_display = risk_scores[
        [
            "city_name",
            "current_pm25",
            "forecast_trend",
            "city_risk_score",
            "risk_level",
            "sustainability_action",
        ]
    ].copy()

    risk_display = risk_display.rename(
        columns={
            "city_name": "City",
            "current_pm25": "Current PM2.5 (μg/m³)",
            "forecast_trend": "Forecast trend",
            "city_risk_score": "Prototype risk score (0-100)",
            "risk_level": "Risk level",
            "sustainability_action": "Suggested sustainable action",
        }
    )

    st.dataframe(
        risk_display,
        width="stretch",
        hide_index=True,
    )

    with st.expander("How this prototype score works"):
        st.write(
            "PM2.5 is the main input. Low wind and very little rainfall can "
            "add a small context adjustment because they may limit pollutant "
            "dispersion. Cities with no fresh monitored PM2.5 stay unavailable."
        )

if LOCALITY_PROFILE_FILE.exists():
    locality_profile = pd.read_csv(LOCALITY_PROFILE_FILE)
    locality_profile = locality_profile[
        locality_profile["area_type"].eq("locality")
    ].copy()
    locality_with_data = locality_profile.dropna(
        subset=["hourly_observations"]
    )
    locality_names = locality_profile["area_name"].nunique()
    covered_localities = locality_with_data["area_name"].nunique()
    if locality_with_data.empty:
        unit_status = "Not yet"
    elif (
        locality_with_data["evidence_status"]
        .fillna("")
        .str.contains("unit validation required", case=False)
        .any()
    ):
        unit_status = "No - review units"
    else:
        unit_status = "Yes"

    st.subheader("Locality evidence and hotspot readiness")
    st.caption(
        "Locality-first pilot view. This reports coverage and evidence readiness; "
        "it does not label a locality as a pollution hotspot or identify a source."
    )

    locality_col1, locality_col2, locality_col3 = st.columns(3)
    locality_col1.metric(
        "Configured locality pilots",
        locality_names,
    )
    locality_col2.metric(
        "Localities with downloaded evidence",
        f"{covered_localities} / {locality_names}",
    )
    locality_col3.metric(
        "All downloaded units ready",
        unit_status,
    )

    locality_summary = (
        locality_profile.groupby(
            ["area_id", "area_name", "district_or_city", "latitude", "longitude"],
            dropna=False,
            as_index=False,
        )
        .agg(
            covered_pollutants=(
                "pollutant_code",
                lambda values: ", ".join(sorted(values.dropna().astype(str).unique()))
                or "No usable hourly evidence",
            ),
            hourly_observations=("hourly_observations", "sum"),
            reporting_stations=("reporting_stations", "max"),
            nearest_station_distance_metres=("nearest_station_distance_metres", "min"),
            spatial_resolution=("spatial_resolution", "first"),
        )
    )
    locality_summary["coverage_state"] = locality_summary[
        "hourly_observations"
    ].fillna(0).map(
        lambda observations: (
            "Evidence available — review required"
            if observations > 0
            else "Evidence gap — collect or approve a source"
        )
    )
    locality_summary["marker_color"] = locality_summary["hourly_observations"].fillna(
        0
    ).map(lambda observations: [34, 197, 94, 210] if observations > 0 else [148, 163, 184, 210])

    st.subheader("Delhi locality pilot coverage map")
    st.caption(
        "Each marker is a configured pilot anchor, not a ward boundary or a monitor. "
        "Green means nearby-station proxy evidence was downloaded; grey means the "
        "pilot needs an approved or working local source before hotspot modelling.")
    locality_map = pdk.Deck(
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=locality_summary,
                get_position="[longitude, latitude]",
                get_fill_color="marker_color",
                get_radius=1100,
                pickable=True,
                auto_highlight=True,
            ),
            pdk.Layer(
                "TextLayer",
                data=locality_summary,
                get_position="[longitude, latitude]",
                get_text="area_name",
                get_color=[240, 244, 248, 230],
                get_size=13,
                get_alignment_baseline="bottom",
                get_pixel_offset=[0, -12],
            ),
        ],
        initial_view_state=pdk.ViewState(
            latitude=28.61,
            longitude=77.12,
            zoom=9.7,
            pitch=0,
        ),
        tooltip={
            "html": "<b>{area_name}</b><br/>{district_or_city}<br/>"
            "Coverage: {coverage_state}<br/>Pollutants: {covered_pollutants}<br/>"
            "Spatial label: {spatial_resolution}<br/>Nearest station: "
            "{nearest_station_distance_metres} m<br/>Nearby station observations: "
            "{hourly_observations}",
        },
    )
    st.pydeck_chart(locality_map, width="stretch", height=420)

    locality_columns = [
        "area_name",
        "pollutant_code",
        "hourly_observations",
        "reporting_stations",
        "freshness_hours_at_download",
        "median_measurement_coverage_percent",
        "nearest_station_distance_metres",
        "spatial_resolution",
        "evidence_status",
    ]
    locality_display = locality_profile[
        [column for column in locality_columns if column in locality_profile]
    ].rename(
        columns={
            "area_name": "Locality",
            "pollutant_code": "Pollutant",
            "hourly_observations": "Hourly observations",
            "reporting_stations": "Reporting stations",
            "freshness_hours_at_download": "Freshness at download (hours)",
            "median_measurement_coverage_percent": "Median provider coverage (%)",
            "nearest_station_distance_metres": "Nearest station distance (m)",
            "spatial_resolution": "Spatial resolution",
            "evidence_status": "Evidence status",
        }
    )
    st.dataframe(locality_display, width="stretch", hide_index=True)

    with st.expander("When a locality becomes a candidate hotspot"):
        st.write(
            "The system needs a recent quality-checked elevated observation or a "
            "validated anomaly, evidence freshness and locality confidence, comparison "
            "with a local baseline or nearby observations, and a human-review case. "
            "Industrial/rural context alone is never proof of a pollution source."
        )

if LOCALITY_FORECAST_FILE.exists():
    locality_forecasts = pd.read_csv(LOCALITY_FORECAST_FILE)
    if not locality_forecasts.empty:
        horizon_order = {"1h": 1, "3h": 3, "4h": 4}
        locality_forecasts["horizon_order"] = locality_forecasts["horizon"].map(
            horizon_order
        )
        locality_forecasts = locality_forecasts.sort_values(
            ["area_name", "horizon_order"]
        )
        st.subheader("Delhi locality early-warning research forecasts")
        st.caption(
            "Separate locality models using historical, quality-gated nearby-station "
            "proxy evidence. These are prototype forecasts with empirical uncertainty, "
            "not live alerts or official AQI values.")
        locality_forecast_columns = [
            "area_name",
            "horizon",
            "current_pm25_input",
            "predicted_pm25",
            "selected_model",
            "empirical_interval_low",
            "empirical_interval_high",
            "forecast_status",
        ]
        st.dataframe(
            locality_forecasts[
                [
                    column
                    for column in locality_forecast_columns
                    if column in locality_forecasts
                ]
            ].rename(
                columns={
                    "area_name": "Locality",
                    "horizon": "Forecast horizon",
                    "current_pm25_input": "Current PM2.5 input (µg/m³)",
                    "predicted_pm25": "Predicted PM2.5 (µg/m³)",
                    "selected_model": "Selected prototype candidate",
                    "empirical_interval_low": "Prototype low range",
                    "empirical_interval_high": "Prototype high range",
                    "forecast_status": "Status",
                }
            ),
            width="stretch",
            hide_index=True,
        )

st.subheader("Monitored cities on the India map")

map_data = active_cities.copy()

if risk_scores is not None:
    map_data = map_data.merge(
        risk_scores[
            [
                "city_id",
                "city_risk_score",
                "risk_level",
            ]
        ],
        on="city_id",
        how="left",
    )

    risk_colors = {
        "Low": [34, 197, 94, 210],
        "Moderate": [234, 179, 8, 210],
        "High": [245, 158, 11, 220],
        "Very High": [220, 38, 38, 230],
    }
    map_data["risk_color"] = map_data["risk_level"].map(risk_colors)
    map_data["risk_color"] = map_data["risk_color"].apply(
        lambda color: color if isinstance(color, list) else [100, 116, 139, 190]
    )
else:
    map_data["risk_level"] = "Risk score unavailable"
    map_data["city_risk_score"] = pd.NA
    map_data["risk_color"] = [[255, 110, 0, 190]] * len(map_data)

map_data["pm25_radius"] = (
    map_data["current_pm25"] * 1200
) + 25000

india_map = pdk.Deck(
    map_style=None,
    initial_view_state=pdk.ViewState(
        latitude=22.5,
        longitude=79.0,
        zoom=4.2,
        pitch=0,
    ),
    layers=[
        pdk.Layer(
            "ScatterplotLayer",
            data=map_data,
            get_position="[longitude, latitude]",
            get_radius="pm25_radius",
            get_fill_color="risk_color",
            pickable=True,
            auto_highlight=True,
        )
    ],
    tooltip={
        "text": (
            "{city_name}\n"
            "PM2.5: {current_pm25} μg/m³\n"
            "Risk: {risk_level} ({city_risk_score}/100)\n"
            "Reporting stations: {reporting_stations}"
        )
    },
)

st.pydeck_chart(
    india_map,
    width="stretch",
    height=500,
)
st.subheader("City conditions")

display_table = city_conditions[
    [
        "city_name",
        "state",
        "current_pm25",
        "reporting_stations",
        "temperature_c",
        "humidity_percent",
        "wind_speed_kmh",
        "precipitation_mm",
    ]
].copy()

display_table["data_status"] = display_table[
    "current_pm25"
].notna().map(
    {
        True: "Fresh monitored PM2.5",
        False: "No fresh monitored data",
    }
)

display_table = display_table.rename(
    columns={
        "city_name": "City",
        "state": "State",
        "current_pm25": "Current PM2.5 (μg/m³)",
        "reporting_stations": "Reporting stations",
        "temperature_c": "Temperature (°C)",
        "humidity_percent": "Humidity (%)",
        "wind_speed_kmh": "Wind speed (km/h)",
        "precipitation_mm": "Rainfall (mm)",
        "data_status": "Data status",
    }
)

st.dataframe(
    display_table,
    width="stretch",
    hide_index=True,
)

st.subheader("City detail")

selected_city_name = st.selectbox(
    "Choose a city",
    city_conditions["city_name"],
)

selected_city = city_conditions[
    city_conditions["city_name"] == selected_city_name
].iloc[0]

if risk_scores is not None:
    selected_risk = risk_scores[
        risk_scores["city_id"] == selected_city["city_id"]
    ]

    if not selected_risk.empty:
        selected_risk = selected_risk.iloc[0]
        st.markdown(
            f"**Prototype risk level:** {selected_risk['risk_level']}"
        )
        st.caption(
            "Suggested sustainable action: "
            f"{selected_risk['sustainability_action']}"
        )

if pd.isna(selected_city["current_pm25"]):
    st.warning(
        f"No fresh monitored PM2.5 reading is available "
        f"for {selected_city_name} right now."
    )
else:
    detail1, detail2, detail3 = st.columns(3)

    detail1.metric(
        "Current PM2.5",
        f"{selected_city['current_pm25']:.1f} μg/m³",
    )

    detail2.metric(
        "Temperature",
        f"{selected_city['temperature_c']:.1f} °C",
    )

    detail3.metric(
        "Humidity",
        f"{selected_city['humidity_percent']:.0f}%",
    )

    st.write(
        f"Reporting stations: "
        f"{int(selected_city['reporting_stations'])}"
    )

    st.write(
        f"Wind speed: "
        f"{selected_city['wind_speed_kmh']:.1f} km/h"
    )

    st.write(
        f"Rainfall: "
        f"{selected_city['precipitation_mm']:.1f} mm"
    )
