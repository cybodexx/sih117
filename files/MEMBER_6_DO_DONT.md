# MEMBER 6 — Team Lead / Integration Architect · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena.

**Tumhara area:** `docker-compose*.yml`, `Makefile`, `.pre-commit-config.yaml`, `tools/**`,
`.github/workflows/**`, `services/llm/ollama_client.py`, `docs/**`, `eval/latency.py`.
Tum poore system ke integration ke owner ho, isliye baaki sab briefs bhi high-level pe pata
hone chahiye.

---

## ❌ YEH MAT KARO

1. **DNS/egress fail ho raha ho toh network me hole mat karo "fix" karne ke liye.** Agar koi
   service internal network pe fail ho raha hai (font fetch, telemetry ping, health check),
   toh us service ko fix karo — egress ka rasta khol kar mat "solve" karo. Yeh sovereignty
   claim ka poora point hai.
2. **Models/wheels ko network cut hone ke BAAD download karne ki koshish mat karo.**
   Two-stage build order fix rakho: pehle connected provisioning (models+wheels), phir sealed
   runtime. Day 17 pe pata chalna ki `pip` ko internet chahiye — classic hackathon death hai.
3. **8GB GPU pe text model + vision model + reranker ko ek saath load karne ki umeed mat
   rakho.** Sequence me load karo, text model warm rakho, image aane pe ek-baar ka swap cost
   accept karo (aur document karo).
4. **`main` branch pe Day 3 ke baad seedha commit mat karo.** Sab `feat/m{n}-*` → `dev` →
   (green smoke test ke baad) `main`.
5. **Contract freeze (Day 2) ko chair karne me late mat karo.** Yeh tumhari zimmedari hai —
   iske bina M1 aur M5 dono block ho jate hain.

## ✅ YEH ZAROOR KARO

1. `services/llm/ollama_client.py` ko poore codebase ka **single LLM entry point** banao —
   async, streaming, retries, timeouts sab isi me. Koi bhi member seedha Ollama ko call na kare.
2. `tools/check_loc.py` (300-LOC gate) Day 1 pe hi commit karo, CI me wire karo — baad me
   dalne se sabka already-likha code red ho jayega.
3. Physical unplug rehearsal karo (`docker-compose.airgap.yml`) — ethernet nikaal ke check
   karo ki demo mid-way pe bhi chalta rahe. Yeh sovereignty ka sabse convincing proof hai.
4. Daily smoke test (`make up && make smoke`) khud chalao aur channel me post karo — issues
   Day-4 se hi pakdo, Day-16 pe nahi.
5. Har `correlation_id` se poora turn trace ho sake (API → worker → agent) — structured
   logging aggregate karo.

## 🔗 Integration me dhyan rakhna

- Tum sabke blockers ka central point ho. Agar koi member 2 ghante se block hai aur khud nahi
  bol raha, tumhe proactively poochna hai daily sync me.
- Review pairing: M6↔M1. P4 tumhara "float phase" hai — profiling + M5/M4 ke code ka LOC/
  modularity cross-review karne ka time hai, idle time nahi.
