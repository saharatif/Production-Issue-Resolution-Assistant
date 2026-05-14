"""Seed Pinecone with Module 1 manufacturing knowledge-base documents.

Required environment:
  OPENAI_API_KEY
  PINECONE_API_KEY
  PINECONE_INDEX (optional, defaults to manufacturing-kb)
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

load_dotenv()


INDEX_NAME = os.getenv("PINECONE_INDEX", "manufacturing-kb")
EMBEDDING_DIMENSION = 1536


DOCUMENTS: list[dict[str, Any]] = [
    {
        "id": "INC-2026-0312-LINE-B-004",
        "text": (
            "Incident INC-2026-0312-LINE-B-004. PLANT-01, LINE-B, PRESS-VALVE-23. "
            "Date: 2026-03-12. Pressure dropped below operating threshold and production output "
            "decreased by 38 percent. Root cause was pressure valve actuator drift after extended "
            "runtime. Corrective action was valve recalibration and actuator response verification."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23",
            "document_type": "incident_report",
            "date": "2026-03-12",
            "tags": ["pressure", "output_drop", "valve_tuning", "LINE-B"],
        },
    },
    {
        "id": "INC-2026-0502-LINE-B-006",
        "text": (
            "Incident INC-2026-0502-LINE-B-006. PLANT-01, LINE-B, PRESS-VALVE-23. "
            "Date: 2026-05-02. Intermittent low pressure and unstable output occurred during "
            "morning shift startup. Operator notes mentioned delayed actuator response. Temporary "
            "stabilization used low-speed mode until maintenance inspected the valve assembly."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23",
            "document_type": "incident_report",
            "date": "2026-05-02",
            "tags": ["pressure", "startup", "actuator_delay", "LINE-B"],
        },
    },
    {
        "id": "MNT-2026-0428-009",
        "text": (
            "Maintenance record MNT-2026-0428-009. PRESS-VALVE-23, LINE-B. Date: 2026-04-28. "
            "Preventive inspection found minor actuator response delay during pressure ramp test. "
            "Valve was cleaned and response tested. Repeat calibration was recommended at planned downtime."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23",
            "document_type": "maintenance_record",
            "date": "2026-04-28",
            "tags": ["pressure", "valve", "calibration", "preventive"],
        },
    },
    {
        "id": "MNT-2026-0510-014",
        "text": (
            "Maintenance record MNT-2026-0510-014. PRESS-VALVE-23, LINE-B. Date: 2026-05-10. "
            "Technician observed slight hydraulic fluid discoloration and sluggish valve response "
            "under load. Fluid level was topped off, but actuator calibration was deferred."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23",
            "document_type": "maintenance_record",
            "date": "2026-05-10",
            "tags": ["pressure", "hydraulic", "deferred_calibration", "maintenance"],
        },
    },
    {
        "id": "SOP-LINE-B-PRESSURE-001",
        "text": (
            "SOP-LINE-B-PRESSURE-001. Pressure Control Procedure for Line B. If pressure drops "
            "below 4.8 bar, reduce line speed to 30 percent, inspect the pressure valve actuator "
            "and hydraulic fluid level, verify sensor signal integrity, and notify maintenance. "
            "If pressure is below 3.5 bar, initiate immediate line stop."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "LINE-B",
            "machine_id": "PRESS-VALVE-23",
            "document_type": "SOP",
            "date": "2026-01-15",
            "tags": ["pressure", "valve", "procedure", "LINE-B"],
        },
    },
    {
        "id": "SOP-THERM-001",
        "text": (
            "SOP-THERM-001. Thermal Anomaly Response. If temperature exceeds 90 C, reduce "
            "throughput by 50 percent and inspect lubrication. If temperature exceeds 150 C, stop "
            "the line immediately, isolate the heat source, notify the shift supervisor, and apply "
            "lockout tagout before inspection."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "",
            "machine_id": "",
            "document_type": "SOP",
            "date": "2026-01-15",
            "tags": ["temperature", "bearing", "thermal", "loto"],
        },
    },
    {
        "id": "STD-MFG-SAFETY-QUALITY-001",
        "text": (
            "Manufacturing safety and quality standards bundle. ISO 9001:2015 Clause 8.5.1 "
            "requires controlled production conditions and monitoring evidence. ISO 13849 guidance "
            "requires abnormal safety-related parameters to trigger a safe state for protected "
            "machinery. OSHA 1910.147 requires hazardous energy isolation and verification before "
            "maintenance work begins."
        ),
        "metadata": {
            "plant_id": "PLANT-01",
            "line_id": "",
            "machine_id": "",
            "document_type": "standard",
            "date": "2026-01-01",
            "tags": ["iso_9001", "iso_13849", "osha_1910_147", "quality", "safety"],
        },
    },
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def main() -> None:
    pinecone_api_key = _require_env("PINECONE_API_KEY")
    _require_env("OPENAI_API_KEY")

    pc = Pinecone(api_key=pinecone_api_key)
    existing_indexes = {index.name for index in pc.list_indexes()}
    if INDEX_NAME not in existing_indexes:
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    texts = [document["text"] for document in DOCUMENTS]
    all_vectors = embeddings.embed_documents(texts)
    vectors = [
        {
            "id": document["id"],
            "values": vector,
            "metadata": {"text": document["text"], **document["metadata"]},
        }
        for document, vector in zip(DOCUMENTS, all_vectors)
    ]

    pc.Index(INDEX_NAME).upsert(vectors=vectors)
    print(f"Seeded {len(vectors)} documents into Pinecone index '{INDEX_NAME}'.")


if __name__ == "__main__":
    main()
