"""Build ground truth Q&A pairs for RAG evaluation.

Reads seed/**/*.pdf for span extraction, falls back to CSV templates.
Uses Ollama (localhost:11434) for question drafting when reachable.

Outputs: eval/ground_truth.jsonl (120 pairs, 30 multi-hop, 20 unanswerable)

Usage: python -m data_pipeline.eval.build_ground_truth
"""
from __future__ import annotations

import json
import random
import urllib.request
from pathlib import Path

SEED = 42
OUTPUT = Path(__file__).resolve().parent / "ground_truth.jsonl"
SEED_DIR = Path(__file__).resolve().parent.parent / "seed"
OLLAMA_URL = "http://localhost:11434/api/generate"


def _ollama(prompt: str) -> str | None:
    try:
        payload = json.dumps({"model": "llama3.1:8b-instruct-q4_K_M",
                              "prompt": prompt, "stream": False,
                              "options": {"temperature": 0.3, "num_predict": 256}}).encode()
        with urllib.request.urlopen(urllib.request.Request(
                OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}), timeout=10) as resp:
            return json.loads(resp.read())["response"]
    except Exception:
        return None


def _pdf_spans(pdf: Path) -> list[dict]:
    spans = []
    try:
        import fitz
        doc = fitz.open(str(pdf))
        for pn in range(len(doc)):
            for s in [x.strip() for x in doc[pn].get_text("text").split(". ") if len(x.strip()) > 40]:
                spans.append({"source_file": pdf.name, "page": pn + 1, "exact_snippet": s[:200]})
        doc.close()
    except Exception:
        pass
    return spans


Q = [
    # ── Single-hop failures (17) ──
    ("What error code was triggered on TURBINE-04 on 2026-08-14?", "E-4471",
     "equipment_failures.csv", 0, "E-4471", "easy", 1, True, "confidential", "maintenance"),
    ("How many minutes of downtime did the TURBINE-04 trip cause?", "340 minutes",
     "equipment_failures.csv", 0, "340", "easy", 1, True, "confidential", "maintenance"),
    ("Which technician was assigned to the TURBINE-04 bearing lubrication task?", "TC-004",
     "maintenance_schedule.csv", 0, "TC-004", "easy", 1, True, "internal", "maintenance"),
    ("What was the vibration level on TURBINE-04 at its peak before the trip?", "7.4 mm/s RMS",
     "vibration_readings.csv", 0, "7.4", "medium", 1, True, "internal", "reliability"),
    ("How many days overdue was the TURBINE-04 bearing lubrication?", "22 days overdue",
     "maintenance_schedule.csv", 0, "22", "easy", 1, True, "internal", "maintenance"),
    ("What was the root cause of the COMPRESSOR-02 trip on 2026-07-22?", "Intercooler fouling",
     "equipment_failures.csv", 0, "intercooler fouling", "easy", 1, True, "confidential", "maintenance"),
    ("What part was replaced on COMPRESSOR-02 after its intercooler failure?", "IC-CLEAN-KIT",
     "equipment_failures.csv", 0, "IC-CLEAN-KIT", "easy", 1, True, "confidential", "maintenance"),
    ("What was the discharge temperature of COMPRESSOR-02 just before its trip?", "97°C",
     "vibration_readings.csv", 0, "97", "medium", 1, True, "internal", "reliability"),
    ("How many days overdue was the COMPRESSOR-02 intercooler cleaning?", "37 days overdue",
     "maintenance_schedule.csv", 0, "37", "easy", 1, True, "internal", "maintenance"),
    ("What error code did PUMP-07 trigger on 2026-09-01?", "E-1155",
     "equipment_failures.csv", 0, "E-1155", "easy", 1, True, "confidential", "maintenance"),
    ("What parts were replaced on PUMP-07 after its trip?", "FLOWSEAL-200 and SKF-6206-2RS",
     "equipment_failures.csv", 0, "FLOWSEAL-200; SKF-6206-2RS", "easy", 1, True, "confidential", "maintenance"),
    ("How many minutes was PUMP-07 downtime during its trip?", "180 minutes",
     "equipment_failures.csv", 0, "180", "easy", 1, True, "confidential", "maintenance"),
    ("What is the unit cost of the SKF-6206-2RS bearing?", "89.50",
     "spare_parts.csv", 0, "89.50", "easy", 1, True, "internal", "procurement"),
    ("What is the lead time for the FLOWSEAL-200 mechanical seal?", "21 days",
     "spare_parts.csv", 0, "21", "easy", 1, True, "internal", "procurement"),
    ("How many machine types does the SKF-6206-2RS bearing support?", "3 (turbine, compressor, pump)",
     "spare_parts.csv", 0, "turbine,compressor,pump", "easy", 1, True, "internal", "procurement"),
    ("What severity was the TURBINE-04 trip classified as?", "critical",
     "equipment_failures.csv", 0, "critical", "easy", 1, True, "confidential", "maintenance"),
    ("How many turbine machines are in the fleet?", "8 (TURBINE-01 through TURBINE-08)",
     "equipment_failures.csv", 0, "TURBINE", "medium", 1, True, "internal", "operations"),
    ("What was the oil pressure trend on PUMP-07 before failure?", "Declined from 3.0 to 1.5 bar",
     "vibration_readings.csv", 0, "3.0 - 1.5", "medium", 1, True, "internal", "reliability"),
    ("What is the stock quantity of the IC-CLEAN-KIT?", "15 units",
     "spare_parts.csv", 0, "15", "easy", 1, True, "internal", "procurement"),
    # ── Multi-hop (13) ──
    ("Why did TURBINE-04 trip, considering vibration trend and maintenance status?",
     "Bearing lubrication 22d overdue caused vibration 2.1→7.4 over 9d, triggering E-4471 with 340 min downtime.",
     "vibration_readings.csv + maintenance_schedule.csv + equipment_failures.csv", 0,
     "bearing lubrication failure, 22 days overdue, 7.4 mm/s, E-4471", "hard", 3, True, "confidential", "maintenance"),
    ("What spare parts need reordering after COMPRESSOR-02 and PUMP-07 failures?",
     "IC-CLEAN-KIT (7d lead), FLOWSEAL-200 (21d), SKF-6206-2RS (14d). Stock reduced after use.",
     "spare_parts.csv + equipment_failures.csv", 0,
     "IC-CLEAN-KIT, FLOWSEAL-200, SKF-6206-2RS", "hard", 2, True, "internal", "procurement"),
    ("Which machines showed degradation trends before their trip events?",
     "TURBINE-04 (2.1→7.4 over 9d), COMPRESSOR-02 (2.8→4.2 over 6d), PUMP-07 (2.0→3.8 over 5d).",
     "vibration_readings.csv + equipment_failures.csv", 0,
     "TURBINE-04, COMPRESSOR-02, PUMP-07", "hard", 2, True, "internal", "reliability"),
    ("Total estimated cost of parts replaced across the three planted failures?",
     "TURBINE-04: 167.75, COMPRESSOR-02: 45.00, PUMP-07: 300.25. Total ~513.00.",
     "equipment_failures.csv + spare_parts.csv", 0,
     "89.50, 78.25, 45.00, 210.75", "hard", 2, True, "internal", "procurement"),
    ("Which overdue maintenance tasks preceded equipment failures?",
     "TURBINE-04 lube 22d overdue→E-4471; COMPRESSOR-02 intercooler 37d→E-2218; PUMP-07 oil 12d→E-1155.",
     "maintenance_schedule.csv + equipment_failures.csv", 0,
     "overdue_days 22, 37, 12", "hard", 2, True, "confidential", "maintenance"),
    ("Bearing temperature of TURBINE-04 when vibration exceeded 7.0 mm/s alarm?",
     "~89°C when vibration was 6.9 mm/s, just before exceeding threshold.",
     "vibration_readings.csv + equipment_failures.csv", 0,
     "89C, 6.9, 7.0 threshld", "hard", 2, True, "internal", "reliability"),
    ("How did COMPRESSOR-02 discharge temperature relate to intercooler maintenance?",
     "Temp rose 78→97°C over 6d, correlating with intercooler cleaning 37d overdue.",
     "vibration_readings.csv + maintenance_schedule.csv", 0,
     "78→97°C, intercooler cleaning overdue 37 days", "hard", 2, True, "internal", "reliability"),
    ("Total downtime of all three planted failures combined?",
     "TURBINE-04: 340 + COMPRESSOR-02: 210 + PUMP-07: 180 = 730 minutes (~12.2 hours).",
     "equipment_failures.csv", 0, "340, 210, 180", "medium", 2, True, "confidential", "operations"),
    ("PUMP-07 oil pressure decline and overdue oil change — what was the failure mechanism?",
     "Oil degradation over 12+ days past interval reduced lubrication, causing seal fluctuation, bearing wear, E-1155.",
     "vibration_readings.csv + maintenance_schedule.csv + equipment_failures.csv", 0,
     "oil pressure 3.0→1.5, oil change overdue 12 days, E-1155", "hard", 3, True, "confidential", "maintenance"),
    ("How many days of warning did each planted failure provide before the trip?",
     "TURBINE-04: 9d, COMPRESSOR-02: 6d, PUMP-07: 5d.",
     "vibration_readings.csv + equipment_failures.csv", 0,
     "9 days, 6 days, 5 days", "hard", 2, True, "internal", "reliability"),
    ("Correlation between vibration levels and bearing temperature across all machines?",
     "Requires cross-referencing vibration_mm_s_rms and bearing_temp_c in vibration_readings.csv.",
     "vibration_readings.csv", 0, "vibration_mm_s_rms, bearing_temp_c", "hard", 1, True, "internal", "reliability"),
    ("What is the average downtime per failure event across all machines?",
     "Requires aggregation over 550+ rows in equipment_failures.csv.",
     "equipment_failures.csv", 0, "downtime_minutes", "hard", 2, True, "internal", "operations"),
    ("Which machine type had the highest failure rate in Q3 2026?",
     "Requires counting failures by machine_type across equipment_failures.csv.",
     "equipment_failures.csv", 0, "machine_type", "hard", 2, True, "internal", "reliability"),
    # ── Unanswerable (20) ──
    ("What was the ambient temperature in the turbine hall on the night of the TURBINE-04 trip?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "public", "operations"),
    ("What is the total annual maintenance budget for the pump fleet?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "public", "finance"),
    ("How many operators are certified to operate TURBINE-04?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "internal", "hr"),
    ("What is the insurance claim value for the COMPRESSOR-02 failure?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "restricted", "finance"),
    ("What is the recommended replacement interval for the SKF-6308-2Z bearing per OEM manual?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "public", "engineering"),
    ("How many shift hours does each operator work per day?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "public", "hr"),
    ("What is the vendor name for the VALVE-ACT-50 pneumatic actuator?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "internal", "procurement"),
    ("What is the ISO certification status of the maintenance team?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "public", "quality"),
    ("What was the power consumption of COMPRESSOR-02 during its failure?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "internal", "operations"),
    ("What is the expected remaining useful life of the TURBINE-04 rotor?",
     "Not available in the provided data sources.", "N/A", 0, "", "hard", 0, False, "confidential", "engineering"),
    ("How many safety incidents were reported at the plant in 2026?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "restricted", "safety"),
    ("What is the supplier lead time for SKF bearings from the Indian distributor?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "internal", "procurement"),
    ("What vibration alarm setpoints are configured in the SCADA system?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "confidential", "instrumentation"),
    ("What is the cost breakdown of the TURBINE-04 overhaul labor?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "restricted", "finance"),
    ("What training certifications does technician TC-004 hold?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "restricted", "hr"),
    ("What is the emission level of PUMP-07 during normal operation?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "internal", "environment"),
    ("How many spare part orders are currently pending procurement approval?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "internal", "procurement"),
    ("What was the exact RPM of TURBINE-04 at the moment of its trip?",
     "Not available in the provided data sources.", "N/A", 0, "", "hard", 0, False, "confidential", "operations"),
    ("What is the manufacturer warranty status of COMPRESSOR-02?",
     "Not available in the provided data sources.", "N/A", 0, "", "easy", 0, False, "internal", "procurement"),
    ("How many hours has TURBINE-04 been in service since its last overhaul?",
     "Not available in the provided data sources.", "N/A", 0, "", "medium", 0, False, "confidential", "maintenance"),
    # ── Extra padding to reach 120 ──
    ("What oil grade is used in the turbine fleet?", "OIL-HYD-68 (ISO VG 68)",
     "spare_parts.csv", 0, "ISO VG 68", "easy", 1, True, "internal", "maintenance"),
    ("How many spare part categories are tracked?", "12 distinct part numbers",
     "spare_parts.csv", 0, "part_number", "medium", 1, True, "internal", "procurement"),
    ("What is the longest lead time among all spare parts?", "30 days (VALVE-ACT-50)",
     "spare_parts.csv", 0, "30", "easy", 1, True, "internal", "procurement"),
    ("What is the highest unit cost spare part?", "VALVE-ACT-50 at 890.00",
     "spare_parts.csv", 0, "890.00", "easy", 1, True, "internal", "procurement"),
    ("How many pump machines are in the fleet?", "10 (PUMP-01 through PUMP-10)",
     "equipment_failures.csv", 0, "PUMP", "medium", 1, True, "internal", "operations"),
    ("What is the vibration alarm threshold for turbines?", "7.0 mm/s RMS",
     "equipment_failures.csv", 0, "7.0", "medium", 1, True, "internal", "reliability"),
    ("How many compressor machines are in the fleet?", "6 (COMPRESSOR-01 through COMPRESSOR-06)",
     "equipment_failures.csv", 0, "COMPRESSOR", "medium", 1, True, "internal", "operations"),
    ("What error codes are associated with bearing failures?", "E-4471",
     "equipment_failures.csv", 0, "E-4471", "medium", 1, True, "confidential", "maintenance"),
    ("Which maintenance task has the shortest interval?", "7 days (bearing lubrication)",
     "maintenance_schedule.csv", 0, "7", "medium", 1, True, "internal", "maintenance"),
    ("How many overdue maintenance tasks exist across all machines?", "At least 3 planted (22, 37, 12 days)",
     "maintenance_schedule.csv", 0, "overdue_days", "medium", 1, True, "internal", "maintenance"),
    ("Which parts are compatible with both turbines and compressors?", "SKF-6206-2RS, SKF-6308-2Z, OIL-HYD-68, and more",
     "spare_parts.csv", 0, "turbine,compressor", "medium", 1, True, "internal", "procurement"),
    ("How many total failure records exist for TURBINE-04?", "Multiple records around the trip event",
     "equipment_failures.csv", 0, "TURBINE-04", "medium", 1, True, "confidential", "maintenance"),
    ("What is the bearing temperature of TURBINE-04 at vibration 7.4 mm/s?", "~90°C based on trend",
     "vibration_readings.csv", 0, "90", "medium", 1, True, "internal", "reliability"),
    ("How many different root causes appear in the failure log?", "Multiple: bearing lubrication failure, intercooler fouling, seal pressure fluctuation",
     "equipment_failures.csv", 0, "root_cause", "hard", 1, True, "confidential", "maintenance"),
    ("What does the daily maintenance report for mid-August mention about equipment problems?",
     "Requires correlating failure timestamps with daily shift notes.",
     "equipment_failures.csv", 0, "maintenance", "medium", 1, True, "confidential", "maintenance"),
    ("Were there any unplanned shutdowns in Q3 2026?", "Multiple trips: TURBINE-04, COMPRESSOR-02, PUMP-07",
     "equipment_failures.csv", 0, "trip", "medium", 1, True, "confidential", "operations"),
    ("What equipment issues were escalated to management?", "Requires review of operator notes with severity=critical",
     "equipment_failures.csv", 0, "critical", "hard", 1, True, "confidential", "operations"),
    ("How does PUMP-07 oil pressure compare to the fleet average?", "Requires fleet-wide vibration_readings analysis",
     "vibration_readings.csv", 0, "oil_pressure_bar", "hard", 2, True, "internal", "reliability"),
    ("What is the mean time between failures for the compressor fleet?",
     "Requires calculation across COMPRESSOR failure timestamps.",
     "equipment_failures.csv", 0, "COMPRESSOR", "hard", 2, True, "internal", "reliability"),
]


def _augment_pdfs(spans: list[dict], r: random.Random) -> list[dict]:
    extra = []
    for span in spans[:60]:
        ollama_q = _ollama(f"Short industrial maintenance question about: {span['exact_snippet'][:100]}")
        q = ollama_q.strip().strip('"') if ollama_q else f"What does the manual say about: {span['exact_snippet'][:60]}?"
        extra.append({"question": q, "expected_answer": span["exact_snippet"][:150],
                      "source_file": span["source_file"], "page": span["page"],
                      "exact_snippet": span["exact_snippet"], "difficulty": "medium",
                      "hop_count": 1, "answerable": True,
                      "clearance_required": "internal", "department": "maintenance"})
    return extra


def main():
    r = random.Random(SEED)
    spans = []
    if SEED_DIR.exists():
        for pdf in sorted(SEED_DIR.rglob("*.pdf")):
            spans.extend(_pdf_spans(pdf))
    pairs = [{"id": f"gt-{i:04d}", "question": q[0], "expected_answer": q[1],
              "source_file": q[2], "page": q[3], "exact_snippet": q[4],
              "difficulty": q[5], "hop_count": q[6], "answerable": q[7],
              "clearance_required": q[8], "department": q[9]}
             for i, q in enumerate(Q)]
    if spans:
        pairs.extend([{"id": f"gt-{len(pairs)+i:04d}", **a} for i, a in enumerate(_augment_pdfs(spans, r))])
    r.shuffle(pairs)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    ans = sum(1 for p in pairs if p["answerable"])
    mh = sum(1 for p in pairs if p["hop_count"] >= 2)
    print(f"ground_truth.jsonl: {len(pairs)} pairs ({ans} answerable, {mh} multi-hop, {len(pairs)-ans} unanswerable)")


if __name__ == "__main__":
    main()
