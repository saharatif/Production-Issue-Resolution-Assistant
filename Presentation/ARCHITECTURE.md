# System Architecture

```mermaid
flowchart TD
    subgraph Browser["🖥️ Browser — React / Vite (port 5173)"]
        UI1[SensorStreamPanel\nLive SSE table]
        UI2[TriggerButton\nScenario selector]
        UI3[AgentPipelineStatus\nStepper]
        UI4[InvestigatorReport\nVerdict + confidence]
        UI5[ActionPlanPanel\nShift handoff · MR · CAPA]
        UI6[ApprovalGate\nApprove / Reject]
        UI7[PDF Download]
    end

    subgraph API["⚙️ FastAPI Backend (port 8000)"]
        EP1[GET /stream/sensor\nSSE sensor stream]
        EP2[POST /api/issues/analyze\nTrigger pipeline]
        EP3[GET /api/issues/:id\nPoll status]
        EP4[POST /api/issues/:id/approve\nHuman gate]
        EP5[GET /api/reports/:id/pdf\nDownload PDF]
    end

    subgraph Pipeline["🤖 Agent Pipeline — LangGraph"]
        A1["🔍 Scanner Agent\nRule-based anomaly detection\nGroups by line → affected_lines"]
        A2["🧠 Investigator Agent\ngpt-4o-mini · root-cause hypotheses\nConfidence breakdown · KB retrieval"]
        A3["🔧 Technician Agent\ngpt-4o-mini · shift handoff\nMaintenance request · CAPA · PDF"]
    end

    subgraph Services["🗄️ Services"]
        S1[(PostgreSQL\nproduction_issues\npipeline_runs\naudit_log)]
        S2[(Pinecone\nVector KB\nIncidents · SOPs\nMaintenance records)]
        S3[PDF Service\nReportLab\nAction plan PDF]
        S4[Simulation Service\nSensor data generator\nDemo scenarios]
    end

    subgraph External["☁️ External APIs"]
        EX1[OpenAI\ngpt-4o-mini\ntext-embedding-3-small]
    end

    %% Frontend → Backend
    UI1 -->|SSE| EP1
    UI2 -->|POST| EP2
    UI3 & UI4 & UI5 -->|GET poll| EP3
    UI6 -->|POST| EP4
    UI7 -->|GET| EP5

    %% Backend → Pipeline
    EP2 -->|BackgroundTask| A1
    EP1 --> S4

    %% Pipeline flow
    A1 -->|has_anomaly = true| A2
    A2 --> A3
    A3 --> S3

    %% Services
    A2 -->|retrieve_similar| S2
    S2 -->|embed query| EX1
    A2 & A3 -->|gpt-4o-mini| EX1
    A3 -->|save_run| S1
    EP4 -->|update_approval\naudit_log| S1
    EP3 -->|get_run| S1
    EP5 --> S3

    %% Styling
    classDef frontend fill:#dbeafe,stroke:#3b82f6,color:#1e3a5f
    classDef backend fill:#dcfce7,stroke:#22c55e,color:#14532d
    classDef agent fill:#fef9c3,stroke:#eab308,color:#713f12
    classDef service fill:#f3e8ff,stroke:#a855f7,color:#581c87
    classDef external fill:#ffe4e6,stroke:#f43f5e,color:#881337

    class UI1,UI2,UI3,UI4,UI5,UI6,UI7 frontend
    class EP1,EP2,EP3,EP4,EP5 backend
    class A1,A2,A3 agent
    class S1,S2,S3,S4 service
    class EX1 external
```

## Component Summary

| Layer | Technology | Role |
|---|---|---|
| **Frontend** | React · Vite · Tailwind · shadcn/ui | SSE consumer, pipeline status, approval UI, PDF download |
| **Backend** | FastAPI · uvicorn | REST + SSE endpoints, background task orchestration |
| **Scanner Agent** | Python rule engine | Classifies sensor readings by rule, groups anomalies per line |
| **Investigator Agent** | gpt-4o-mini + Pinecone RAG | Root-cause hypotheses, confidence breakdown, recommendations |
| **Technician Agent** | gpt-4o-mini | Shift handoff note, maintenance request, CAPA, PDF trigger |
| **PostgreSQL** | asyncpg · 9 tables | Pipeline state, audit log, approval workflow |
| **Pinecone** | Vector search | Historical incidents, SOPs, maintenance records |
| **PDF Service** | ReportLab | Branded corrective action plan PDF |
| **OpenAI** | gpt-4o-mini + embeddings | LLM inference and vector embeddings |

## Data Flow

```
Sensor SSE stream
    └─▶ Frontend displays live readings
            └─▶ Plant manager clicks Analyze
                    └─▶ POST /api/issues/analyze  (returns issue_id immediately)
                            └─▶ Background: Scanner → Investigator → Technician
                                    └─▶ GET /api/issues/:id  (frontend polls)
                                            └─▶ Plant manager reviews + Approves
                                                    └─▶ POST /api/issues/:id/approve
                                                            └─▶ Audit log written
                                                                    └─▶ GET /api/reports/:id/pdf
```
