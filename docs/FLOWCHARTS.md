# AirSentinel workflow diagrams

These are the submission-ready flows. Contextual evidence never proves a pollution source, and automated logic never performs enforcement.

## 1. Complete evidence-to-action workflow

```mermaid
flowchart LR
    A[Authorised official/current station data when configured\nPM2.5 PM10 NO2 O3 SO2 CO] --> F[Canonical record\nsource unit UTC quality station]
    B[Historical development fallback\nprovenance labelled] --> F
    C[Weather] --> F
    D[Earth Engine satellite context] --> G[Context only]
    E[Consented text photo voice] --> H[Identity moderation privacy]
    F --> I[Freshness range duplicate distance coverage gates]
    G --> I
    H --> I
    I --> J[1h 3h 4h gated research forecast + uncertainty]
    I --> K[Observed-vs-expected residual]
    J --> K
    K --> L{Large or unsupported change?}
    L -- No --> M[Reviewed public aggregate]
    L -- Yes --> N[Unexpected-spike or evidence-gap case\ncause unverified]
    N --> O[Human authority review]
    O --> P[Audited sustainable response]
```

## 2. Locality evidence gate

```mermaid
flowchart TD
    A[Defined locality geometry or approved pilot anchor] --> B[Discover nearby stations]
    B --> C[Retain provider station ID distance unit and time]
    C --> D{Fresh quality-controlled rows?}
    D -- No --> E[Evidence gap\nno locality AQI or hotspot label]
    D -- Yes --> F{180+ day span and sufficient completeness?}
    F -- No --> G[Continue collection\nshow data-candidate status]
    F -- Yes --> H[Join weather and build leakage-safe features]
    H --> I[Chronological train/validation/test]
    I --> J[Compare persistence with conventional boosting]
    J --> K[Human-approved research candidate]
```

## 3. Sudden spike and forecast-failure safeguard

```mermaid
flowchart TD
    A[New monitored observation] --> C[Compare with forecast interval]
    B[Forecast + empirical uncertainty] --> C
    C --> D{Outside expected range?}
    D -- No --> E[Continue monitored view]
    D -- Yes --> F[Create unexpected-spike review case]
    F --> G[Label cause unverified]
    G --> H[Check neighbouring stations and sensor health]
    H --> I[Check wind rain fire/satellite and moderated reports]
    I --> J[Reviewer decides: monitor inspect escalate or close]
    J --> K[Write immutable audit event]
```

## 4. Citizen multimodal and accessibility flow

```mermaid
flowchart TD
    A[Verified citizen consent] --> B{Input type}
    B -->|Text| C[Privacy minimisation]
    B -->|Photo| D[In-memory Gemini description\nno identity or source claim]
    B -->|Voice| E[Speech-to-Text]
    E --> C
    D --> C
    C --> F[Optional Translation]
    F --> G[Firebase pending review]
    G --> H[Moderation and coarse-area aggregation]
    H --> I[Supporting evidence visible to reviewer]
    I --> J[Optional Text-to-Speech reviewed guidance]
```

## 5. Google Cloud deployment flow

```mermaid
flowchart TD
    A[Team-owned GCP project billing and region] --> B[Enable only required APIs]
    B --> C[Runtime service accounts + Secret Manager]
    C --> D[Firebase Auth and deny-by-default rules]
    C --> E[BigQuery governed analytical tables]
    C --> F[Gemini Maps Earth Engine language services]
    D --> G[Private Cloud Run API]
    E --> G
    F --> G
    G --> H[Private authority portal\nhuman review]
    G --> I[Public aggregate dashboard\nno personal evidence]
    H --> J[Identity audit and end-to-end URL tests]
    I --> J
```

## Non-negotiable interpretation rules

1. A nearby station is a locality proxy unless a monitor is physically verified inside the approved geometry.
2. CPCB/data.gov.in is the preferred official Indian current source; a fallback must remain visibly labelled.
3. Satellite, weather, a photo, a purifier or one citizen report cannot independently prove source or responsibility.
4. Forecasts are estimates with intervals; a sudden miss creates a review case rather than a confident explanation.
5. Authority actions require identity and are audited. No endpoint automatically publishes an alert, attributes a source or enforces a measure.
