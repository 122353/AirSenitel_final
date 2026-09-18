# AirSentinel Official Data Source Catalog

**Purpose:** a concise, safe source catalogue for India pilot data. A source is not considered integrated merely because it appears here or in the project registry. Every collection must preserve provenance, access conditions, timestamp, units, and a permitted-use label.

## Primary ground-observation sources

| Source | Access and expected data | Allowed role | Hard limit |
| --- | --- | --- | --- |
| CPCB real-time AQI via data.gov.in | API key; hourly current snapshots. Catalogue: https://www.data.gov.in/catalog/real-time-air-quality-index | Preferred current official-source station snapshot after QA. | Not a public 180-day bulk archive. Snapshot values still require field and unit checks. |
| CPCB CAAQMS / CCR | Portal or approved export. Portal: https://airquality.cpcb.gov.in/ | Preferred official historical ground truth when a documented export/access agreement is available. | Do not scrape undocumented or CAPTCHA-protected paths. Do not assume a portal page grants bulk-data reuse. |
| State Pollution Control Board archives | Published download/API or approved export. Directory: https://cpcb.nic.in/spcbs-pccs/ | Locality validation supplement and state-specific historical source. | Formats, coverage, licence, and reuse terms vary by state. |

## Context and fallback sources

| Source | Access and expected data | Allowed role | Hard limit |
| --- | --- | --- | --- |
| OpenAQ v3 | API key and provider-dependent historical station observations. Docs: https://docs.openaq.org/ | Historical development fallback while approved official archives are unavailable. | Third-party aggregation. Never label it as official AQI, CPCB ingestion, or regulatory evidence. |
| IMD | Approved data supply or public API where permitted. Reference: https://api.imd.gov.in/public/api_reference.html | Weather context and forecast covariates. | Weather is not a pollutant measurement. |
| ERA5 reanalysis | Copernicus Climate Data Store account/API. Dataset: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels | Long-history weather fallback. | Gridded reanalysis is not a local sensor or a live Indian official observation. |
| Sentinel-5P through Earth Engine | Earth Engine project. Catalogue: https://developers.google.com/earth-engine/datasets/catalog/sentinel-5p | Regional gas/aerosol and corridor context. | Atmospheric columns are not ground-level locality PM or source proof. |
| NASA FIRMS | MAP_KEY API. API: https://firms.modaps.eosdis.nasa.gov/api/area/ | Fire-context review signal. | A detection is not proof of stubble burning or legal source attribution. |

## Source labels that must appear in normalized data

| Situation | Required label | Required interpretation |
| --- | --- | --- |
| Successful CPCB/data.gov.in snapshot | source system: CPCB real-time AQI via data.gov.in; source agency: Central Pollution Control Board | A source-published current snapshot only; AirSentinel does not certify or alter it. |
| Approved CPCB/SPCB historical export | Source system and agency exactly as the approved export identifies them | Historical research after licence, station, unit, and QA checks. |
| OpenAQ historical fallback | source system: OpenAQ v3 historical fallback; source agency: upstream provider exposed through OpenAQ; verify before use | Development-only data; regulatory use prohibited; preserve the upstream licence and source URL. |
| Community or purifier signal | indoor/private or moderated supporting evidence | Never merge with outdoor AQI, publish personal data, or treat it as neighbourhood proof. |

## When official archives or approval are unavailable

1. **For current observations:** collect the authorised CPCB/data.gov.in snapshot on a schedule and archive every raw payload. Do not create fictional historical records from a latest-value endpoint.
2. **For historical model development:** use the OpenAQ fallback with its development-only label, then seek approved CPCB/SPCB exports to replace or validate it.
3. **For weather and event context:** use IMD where approved; otherwise clearly label ERA5, satellite, or FIRMS outputs as contextual development evidence.
4. **For locality gaps:** show a coverage-gap or human-review case, not a local AQI or hotspot claim.
5. **For citizen and device data:** obtain opt-in consent, reduce precision, moderate reports, and separate indoor data from outdoor monitoring.

## Current project position

The current saved historical data is entirely OpenAQ-derived development fallback. No saved CPCB/data.gov.in snapshot or CPCB snapshot archive was found when the accompanying status report was refreshed. Therefore the project can demonstrate provenance-aware historical research and gap reporting, but it must not claim a live official CPCB integration.

See DATA_SOURCE_AND_FALLBACK_POLICY.md for full safety gates and DATA_IMPROVEMENT_STATUS.md for the current verified metrics.
