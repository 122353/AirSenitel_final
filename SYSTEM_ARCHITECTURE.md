# AirSentinel system architecture

## System introduction

AirSentinel is a locality-first evidence and early-warning platform. It addresses the gap between city-wide monitoring and the ward, village-edge, industrial-zone or transport-corridor decision that a public authority actually needs to investigate.

Its core response to an unexpected event is deliberately conservative:

```text
detect a mismatch -> preserve evidence -> mark cause unverified -> request corroboration -> human review -> record an auditable action
```

## Logical architecture

```mermaid
flowchart LR
    subgraph Sources[Evidence sources]
        A[Authorised CPCB/data.gov.in\ncurrent station data when configured]
        B[OpenAQ historical\ndevelopment fallback]
        C[Weather]
        D[Earth Engine satellite context]
        E[Consented citizen text, photo or voice]
    end
    A --> F[Canonical observation and provenance contract]
    B --> F
    C --> F
    D --> G[Context-only layer]
    E --> H[Firebase pending-review evidence]
    F --> I[Quality, coverage and freshness gates]
    G --> I
    H --> I
    I --> J[1h, 3h, 4h conventional forecast candidates]
    I --> K[Unexpected residual and evidence-gap detection]
    J --> K
    K --> L[Human authority review queue]
    L --> M[Audited sustainable response]
    I --> N[BigQuery governed analytics]
    N --> O[Public aggregate dashboard]
```

## Google Cloud target

```mermaid
flowchart TD
    U[Public user] --> P[Public Cloud Run dashboard\naggregate/read-only]
    C[Verified citizen] --> API[Private Cloud Run API]
    R[Authorised reviewer] --> A[Private authority portal]
    API --> F[Firebase Auth + Firestore/Storage rules]
    API --> B[BigQuery approved analytical tables]
    API --> G[Gemini guarded explanation/photo helper]
    API --> M[Maps + Earth Engine contextual layers]
    API --> L[Translation, speech-to-text, text-to-speech]
    A --> B
    A --> F
    S[Secret Manager] --> API
    IAM[Cloud Run IAM / reviewer identity] --> API
    IAM --> A
```

The public dashboard may be unauthenticated only because it exposes reviewed aggregate artifacts. The API and authority portal remain private. Firebase client rules deny direct writes by default; server-side access uses least-privilege Application Default Credentials.

## Model policy

- Use persistence as the first baseline.
- Compare an established conventional tree-boosting candidate on the same chronological hold-out.
- Use empirical uncertainty and publish the hold-out dates.
- No model output is official AQI or a live alert until approved operational validation exists.
- Do not promote deep learning or federated learning in the submission.
- Vertex AI is an optional managed host for a human-approved conventional model, not proof that the model is good.
