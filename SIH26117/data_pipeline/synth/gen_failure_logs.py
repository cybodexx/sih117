"""Generate synthetic CSVs for the AEGIS-WB demo corpus.

Produces: equipment_failures.csv, maintenance_schedule.csv,
          vibration_readings.csv, spare_parts.csv in synth/output/

Planted correlations:
  1. TURBINE-04 vibration 2.1→7.4 over 9d, bearing lube 22d overdue,
     E-4471 trip 2026-08-14T04:12 (340 min).
  2. COMPRESSOR-02 discharge temp 78→97°C over 6d, intercooler fouling,
     E-2218 trip 2026-07-22T11:30 (210 min).
  3. PUMP-07 seal pressure erratic, oil degradation,
     E-1155 trip 2026-09-01T02:45 (180 min).

Usage: python -m data_pipeline.synth.gen_failure_logs
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
OUTPUT = Path(__file__).resolve().parent / "output"
MIDS = [f"TURBINE-{i:02d}" for i in range(1, 9)] + \
       [f"COMPRESSOR-{i:02d}" for i in range(1, 7)] + \
       [f"PUMP-{i:02d}" for i in range(1, 11)]
MTYPES = {m: ("steam_turbine" if "TURBINE" in m else
              "centrifugal_compressor" if "COMPRESSOR" in m else
              "centrifugal_pump") for m in MIDS}
ERR = ["E-1101","E-1155","E-2218","E-3340","E-4471","E-5502","E-6610","E-7733","E-8804","E-9921"]
SEV = ["low","medium","high","critical"]
RES = ["replaced bearing assembly","reset trip and inspected seals","cleaned intercooler fins",
       "replaced oil filter and topped up","tightened coupling bolts","realigned pump impeller",
       "replaced thermocouple","flushed cooling water lines","overhauled valve actuator","replaced gasket set"]
TECH = [f"TC-{i:03d}" for i in range(1, 16)]
OPS = [f"OP-{i:02d}" for i in range(1, 9)]
NOTES = [
    "heard unusual vib near bearing, noted on shift log",
    "brng temp high, tripped @0412, called AE",
    "slight oil leak at seal, will monitor tmrw",
    "dischrg press flctuating ±0.3 bar, snr tech aware",
    "vibraion trending up past 5 mm/s, need inspction",
    "cooling water temp 2 deg above nominal",
    "spare part out of stok, ordered via maint req",
    "alignment check done last wk, looks ok for now",
    "no abnormal readings this shift, all within limits",
    "bearng grease fitting was clogged, cleared it",
    "motor amp draw 2% above rated, monitoring",
    "noticed rust on coupling guard, reported to maint",
    "vibration spikes during startup, settles after 10min",
    "oil press dropped briefly, came back on its own",
]
NOTES_T4 = [
    "vib on TB04 climbing since mon, brng area suspect",
    "TB04 vib at 5.8 mm/s, bearing greas overdue 18 dys",
    "TB04 brng temp 89C, vib 6.9, alarm at 7.0 threshld",
    "TB04 vib hit 7.4 last night, maint called for emerg",
    "brng temp high, tripped @0412, called AE for TB04",
    "E-4471 trip on TB04, brng lube 22 days overdue!!!",
]
NOTES_C2 = [
    "CP02 dischrg temp drifting up past 90C since last wk",
    "intercooler on CP02 looking fouled, fins clogged",
    "CP02 vib peaks at 4.2, was 2.8 last month",
    "E-2218 trip on CP02, intercooler failure confirmed",
    "CP02 dischrg hit 97C before trip, abouve limit",
]
NOTES_P7 = [
    "PMP07 seal press flctuating bad, oil looks dark",
    "PMP07 oil sample came back degraded, change needed",
    "PMP07 bearing noise increased, vib at 3.8 mm/s",
    "E-1155 trip on PMP07, seal and brng failure",
]
TASKS = ["bearing lubrication","seal inspection","vibration analysis","oil change",
         "coupling alignment","cooling system flush","valve overhaul",
         "thermocouple calibration","intercooler cleaning","impeller inspection"]
PARTS = [
    ("SKF-6206-2RS","deep groove ball bearing 30x62x16","turbine,compressor,pump",45,14,89.50),
    ("SKF-6308-2Z","deep groove ball bearing 40x90x23","turbine,compressor",22,14,156.00),
    ("FLOWSEAL-200","mechanical seal 25mm carbon/sic","pump",30,21,210.75),
    ("IC-CLEAN-KIT","intercooler cleaning kit","compressor",15,7,45.00),
    ("OIL-HYD-68","hydraulic oil ISO VG 68 20L","turbine,compressor,pump",60,3,78.25),
    ("TC-KTYPE-100","k-type thermocouple 1m sheath","turbine,compressor,pump",50,5,32.00),
    ("GLAND-SET-P25","gland packing set size 25mm","pump",40,10,18.50),
    ("COUPL-1220","coupling element size 12/20","turbine,pump",18,21,245.00),
    ("FILTER-OIL-10","oil filter element 10 micron","turbine,compressor,pump",100,2,22.75),
    ("VALVE-ACT-50","pneumatic valve actuator 50mm","compressor,pump",8,30,890.00),
    ("O-RING-75A","viton o-ring 75mm AS568","turbine,compressor,pump",80,3,8.50),
    ("VIB-SENSOR-M","vibration sensor mounting kit","turbine,compressor,pump",25,10,145.00),
]


class _Rng:
    def __init__(self, seed: int):
        self._s = seed
    def rand(self) -> float:
        self._s = (self._s * 1103515245 + 12345) & 0x7FFFFFFF
        return self._s / 0x7FFFFFFF
    def choice(self, seq): return seq[int(self.rand() * len(seq))]
    def randint(self, lo, hi): return int(self.rand() * (hi - lo + 1)) + lo
    def gauss(self, mu, sig):
        u1, u2 = self.rand(), self.rand()
        return mu + sig * math.sqrt(-2 * math.log(max(u1, 1e-10))) * math.cos(6.2831853 * u2)
    def shuffle(self, lst):
        for i in range(len(lst) - 1, 0, -1):
            j = int(self.rand() * (i + 1))
            lst[i], lst[j] = lst[j], lst[i]


def _write(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _fail_row(r, ts, mid, ec, sv, dt, note, root="", res="", parts=""):
    return {"timestamp": ts.strftime("%d-%m-%Y %H:%M"), "machine_id": mid,
            "machine_type": MTYPES[mid], "error_code": ec, "severity": sv,
            "downtime_minutes": dt, "operator_notes": note,
            "root_cause": root, "resolution": res, "technician_id": r.choice(TECH),
            "parts_replaced": parts, "operator_id": r.choice(OPS)}


def gen_failures(r: _Rng) -> list[dict]:
    rows = []
    base = datetime(2026, 5, 1)
    for _ in range(550):
        ts = base + timedelta(seconds=int(r.rand() * 120 * 86400))
        mid = r.choice(MIDS)
        rows.append(_fail_row(r, ts, mid, r.choice(ERR), r.choice(SEV),
                              r.randint(15, 420), r.choice(NOTES),
                              r.choice(RES), r.choice(RES),
                              "; ".join(r.choice(RES) for _ in range(r.randint(0, 2)))))
    trip1 = datetime(2026, 8, 14, 4, 12)
    for i, n in enumerate(NOTES_T4):
        ts = trip1 - timedelta(days=9 - i, hours=r.randint(0, 6))
        rows.append(_fail_row(r, ts, "TURBINE-04", r.choice(["E-4471", "E-4471", "E-3340"]),
                              r.choice(["medium", "high", "critical"]),
                              340 if i == 5 else r.randint(0, 45), n,
                              "bearing lubrication failure",
                              "replaced bearing assembly" if i == 5 else "",
                              "SKF-6206-2RS; OIL-HYD-68" if i == 5 else ""))
    trip2 = datetime(2026, 7, 22, 11, 30)
    for i, n in enumerate(NOTES_C2):
        ts = trip2 - timedelta(days=6 - i, hours=r.randint(0, 8))
        rows.append(_fail_row(r, ts, "COMPRESSOR-02", r.choice(["E-2218", "E-2218", "E-5502"]),
                              r.choice(["medium", "high", "critical"]),
                              210 if i == 4 else r.randint(0, 30), n,
                              "intercooler fouling and degradation",
                              "cleaned intercooler fins" if i == 4 else "",
                              "IC-CLEAN-KIT" if i == 4 else ""))
    trip3 = datetime(2026, 9, 1, 2, 45)
    for i, n in enumerate(NOTES_P7):
        ts = trip3 - timedelta(days=5 - i, hours=r.randint(0, 10))
        rows.append(_fail_row(r, ts, "PUMP-07", r.choice(["E-1155", "E-1155", "E-1101"]),
                              r.choice(["medium", "high", "critical"]),
                              180 if i == 3 else r.randint(0, 25), n,
                              "seal pressure fluctuation and oil degradation",
                              "replaced bearing assembly" if i == 3 else "",
                              "FLOWSEAL-200; SKF-6206-2RS" if i == 3 else ""))
    for row in rows:
        for k in ("root_cause", "resolution", "parts_replaced", "operator_notes"):
            if r.rand() < 0.04:
                row[k] = ""
    r.shuffle(rows)
    return rows


def gen_maintenance(r: _Rng) -> list[dict]:
    rows = []
    base = datetime(2026, 9, 1)
    for mid in MIDS:
        for _ in range(r.randint(2, 5)):
            last = base - timedelta(days=r.randint(1, 120))
            interval = r.choice([7, 14, 30, 60, 90, 180])
            nxt = last + timedelta(days=interval)
            rows.append({"machine_id": mid, "task": r.choice(TASKS),
                         "interval_days": interval,
                         "last_performed": last.strftime("%Y-%m-%d"),
                         "next_due": nxt.strftime("%Y-%m-%d"),
                         "overdue_days": max(0, (base - nxt).days),
                         "assigned_to": r.choice(TECH)})
    forced = [
        ("TURBINE-04", "bearing lubrication", 14, "2026-07-19", "2026-08-02", 22, "TC-004"),
        ("COMPRESSOR-02", "intercooler cleaning", 30, "2026-06-15", "2026-07-15", 37, "TC-007"),
        ("PUMP-07", "oil change", 60, "2026-06-20", "2026-08-19", 12, "TC-011"),
    ]
    for mid, task, iv, last, nxt, od, tech in forced:
        rows.append({"machine_id": mid, "task": task, "interval_days": iv,
                     "last_performed": last, "next_due": nxt,
                     "overdue_days": od, "assigned_to": tech})
    r.shuffle(rows)
    return rows


def gen_vibration(r: _Rng) -> list[dict]:
    rows = []
    base = datetime(2026, 6, 1)
    V0 = {"steam_turbine": 2.0, "centrifugal_compressor": 2.5, "centrifugal_pump": 1.8}
    T0 = {"steam_turbine": 62, "centrifugal_compressor": 68, "centrifugal_pump": 55}
    O0 = {"steam_turbine": 4.5, "centrifugal_compressor": 8.2, "centrifugal_pump": 3.0}
    for h in range(90 * 24):
        ts = base + timedelta(hours=h)
        for mid in MIDS:
            mt = MTYPES[mid]
            v = max(0.3, r.gauss(V0[mt], 0.4))
            t = max(30, r.gauss(T0[mt], 3))
            o = max(1.0, r.gauss(O0[mt], 0.3))
            if mid == "TURBINE-04":
                d = (ts - datetime(2026, 8, 5)).total_seconds() / 86400
                if 0 <= d <= 9:
                    v = 2.1 + 5.3 * (d / 9) + r.gauss(0, 0.15)
                    t = 65 + 25 * (d / 9) + r.gauss(0, 1.5)
            if mid == "COMPRESSOR-02":
                d = (ts - datetime(2026, 7, 16)).total_seconds() / 86400
                if 0 <= d <= 6:
                    v = 2.8 + 1.4 * (d / 6) + r.gauss(0, 0.12)
                    t = 78 + 19 * (d / 6) + r.gauss(0, 1.0)
            if mid == "PUMP-07":
                d = (ts - datetime(2026, 8, 27)).total_seconds() / 86400
                if 0 <= d <= 5:
                    v = 2.0 + 1.8 * (d / 5) + r.gauss(0, 0.1)
                    o = 3.0 - 1.5 * (d / 5) + r.gauss(0, 0.15)
            rows.append({"timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
                         "machine_id": mid,
                         "vibration_mm_s_rms": round(v, 2),
                         "bearing_temp_c": round(t, 1),
                         "oil_pressure_bar": round(o, 2)})
    for row in rows:
        for k in ("vibration_mm_s_rms", "bearing_temp_c", "oil_pressure_bar"):
            if r.rand() < 0.04:
                row[k] = ""
    return rows


def gen_parts(r: _Rng) -> list[dict]:
    return [{"part_number": p[0], "description": p[1], "machine_types": p[2],
             "stock_qty": p[3] + r.randint(-5, 10), "lead_time_days": p[4],
             "unit_cost": p[5]} for p in PARTS]


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    r = _Rng(SEED)
    FAIL_FIELDS = ["timestamp","machine_id","machine_type","error_code","severity",
                   "downtime_minutes","operator_notes","root_cause","resolution",
                   "technician_id","parts_replaced","operator_id"]
    _write(OUTPUT / "equipment_failures.csv", gen_failures(r), FAIL_FIELDS)
    _write(OUTPUT / "maintenance_schedule.csv", gen_maintenance(r),
           ["machine_id","task","interval_days","last_performed","next_due",
            "overdue_days","assigned_to"])
    _write(OUTPUT / "vibration_readings.csv", gen_vibration(r),
           ["timestamp","machine_id","vibration_mm_s_rms","bearing_temp_c","oil_pressure_bar"])
    _write(OUTPUT / "spare_parts.csv", gen_parts(r),
           ["part_number","description","machine_types","stock_qty","lead_time_days","unit_cost"])
    for fn in sorted(OUTPUT.iterdir()):
        if fn.suffix == ".csv":
            with open(fn) as f:
                print(f"{fn.name}: {sum(1 for _ in f) - 1} rows")
    print("Done.", OUTPUT)


if __name__ == "__main__":
    main()
