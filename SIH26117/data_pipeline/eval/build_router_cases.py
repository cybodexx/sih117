"""Build 60 labelled intent routing test cases for the supervisor.

10 per intent across 6 routes:
  DOC_QA, VISION, DATA_ANALYSIS, INCIDENT, COMPLIANCE, CHITCHAT

Outputs: eval/router_cases.jsonl

Usage: python -m data_pipeline.eval.build_router_cases
"""
from __future__ import annotations

import json
import random
from pathlib import Path

SEED = 42
OUTPUT = Path(__file__).resolve().parent / "router_cases.jsonl"

INTENTS = {
    "DOC_QA": [
        "What is the recommended bearing clearance for a steam turbine?",
        "Find the torque specification for the coupling bolts on PUMP-03",
        "What does the O&M manual say about intercooler maintenance intervals?",
        "Extract the safety precautions from the lockout-tagout procedure",
        "What is the maximum operating temperature for the SKF-6206-2RS bearing?",
        "Quote the section on seal replacement from the pump maintenance manual",
        "What are the oil analysis pass/fail criteria in the compressor manual?",
        "Find the vibration alarm thresholds documented in the reliability handbook",
        "What does the SOP say about responding to a bearing temperature alarm?",
        "Locate the calibration procedure for the K-type thermocouples",
    ],
    "VISION": [
        "What defects do you see in this photo of the bearing?",
        "Describe the corrosion pattern on this pipe image",
        "Can you identify the damage type in this thermographic image?",
        "What does this P&ID diagram show for the cooling water circuit?",
        "Is this mechanical seal leaking in the attached photo?",
        "Describe the weld defect visible in this radiograph",
        "What readings can you see on this gauge close-up photo?",
        "Analyze the wear pattern on this gear tooth photograph",
        "What does this exploded assembly drawing show?",
        "Is this cable insulation damage consistent with overheating?",
    ],
    "DATA_ANALYSIS": [
        "What is the average vibration trend across all turbines this month?",
        "How does PUMP-07's oil pressure compare to the fleet average?",
        "Show me the failure frequency by machine type for Q3 2026",
        "What is the correlation between vibration levels and bearing temperature?",
        "Calculate the mean time between failures for the compressor fleet",
        "What is the total downtime across all machines in August 2026?",
        "Which machine type has the highest failure rate?",
        "What is the spare parts consumption trend for bearings?",
        "How many overdue maintenance tasks exist across the entire fleet?",
        "What is the average severity distribution of all logged failures?",
    ],
    "INCIDENT": [
        "Why did TURBINE-04 trip on August 14th?",
        "What caused the COMPRESSOR-02 shutdown last month?",
        "Investigate the root cause of the PUMP-07 failure on September 1st",
        "What was the chain of events leading to the turbine E-4471 trip?",
        "Why did the intercooler failure occur on COMPRESSOR-02?",
        "What factors contributed to the pump seal failure?",
        "Trace the degradation timeline for TURBINE-04 before its trip",
        "What was the sequence of failures in the COMPRESSOR-02 incident?",
        "Why did PUMP-07's oil pressure decline before the trip?",
        "What maintenance gaps led to the TURBINE-04 bearing failure?",
    ],
    "COMPLIANCE": [
        "Is the plant compliant with IS 15656 for emergency shutdown procedures?",
        "What ISO 14001 requirements apply to the cooling water system?",
        "Show me the regulatory requirements for pressure vessel inspections",
        "Does the maintenance schedule meet OSHA lockout-tagout standards?",
        "What DPDP Act 2023 requirements apply to our data handling?",
        "Are we compliant with the boiler safety regulations for the turbine?",
        "What are the statutory inspection intervals for the compressor?",
        "Does our audit trail meet the requirements of ISO 9001?",
        "What safety standards govern the electrical panels shown in the photos?",
        "Are the spare parts certifications compliant with BIS standards?",
    ],
    "CHITCHAT": [
        "Hello, how are you today?",
        "What can you help me with?",
        "Thanks for the information",
        "Can you explain what AEGIS-WB is?",
        "What's the weather like outside?",
        "Tell me a joke about maintenance",
        "How does this system work?",
        "Who built this workbench?",
        "Can you translate Hindi to English?",
        "What AI model are you running on?",
    ],
}

META_INTENTS = {
    "DOC_QA": {"agent": "rag_agent", "tools": ["vector_search", "pdf_reader"]},
    "VISION": {"agent": "vision_agent", "tools": ["vlm_caption", "ocr_extract"]},
    "DATA_ANALYSIS": {"agent": "data_agent", "tools": ["sql_query", "chart_gen"]},
    "INCIDENT": {"agent": "investigator", "tools": ["vector_search", "sql_query"]},
    "COMPLIANCE": {"agent": "compliance_agent", "tools": ["vector_search", "web_lookup"]},
    "CHITCHAT": {"agent": "synthesizer", "tools": []},
}


def _choice(r, seq):
    return seq[int(r.random() * len(seq))]


def main():
    r = random.Random(SEED)
    cases: list[dict] = []
    idx = 0

    for intent, questions in INTENTS.items():
        meta = META_INTENTS[intent]
        for q in questions:
            idx += 1
            cases.append({
                "id": f"router-{idx:03d}",
                "intent": intent,
                "question": q,
                "expected_agent": meta["agent"],
                "expected_tools": meta["tools"],
                "difficulty": _choice(r, ["easy", "medium"]),
                "requires_context": intent != "CHITCHAT",
            })

    r.shuffle(cases)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")

    counts = {}
    for c in cases:
        counts[c["intent"]] = counts.get(c["intent"], 0) + 1
    print(f"router_cases.jsonl: {len(cases)} cases")
    for intent, cnt in sorted(counts.items()):
        print(f"  {intent}: {cnt}")


if __name__ == "__main__":
    main()
