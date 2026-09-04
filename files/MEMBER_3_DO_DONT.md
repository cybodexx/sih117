# MEMBER 3 — Backend & Security · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena.

**Tumhara area:** `backend/main.py`, `api/`, `core/`, `db/`, `schemas/`,
`services/{crypto,audit}/`, `tests/security/`. Yeh + tum hi contract file ke author ho.

---

## ❌ YEH MAT KARO

1. **`main.py` ko 60 lines se bada mat hone do.** Sirf routers mount karne ke liye hai —
   koi logic yahan nahi.
2. **API route (`api/`) me business logic mat likho.** Thin controller rakho — logic
   `services/` me jaye. Yeh sabse zyada todha jaane wala rule hai, isse Phase 4 tak file
   800 lines ki ho jayegi agar shuru se sahi nahi kiya.
3. **Client se aaya `clearance`, `department`, ya `filter` field kabhi trust mat karo.**
   `MessageCreate` me agar yeh fields aayein bhi, unhe ignore karo — sirf JWT se identity aayegi
   (contract rule C1). Yeh RBAC ka poora point hai.
4. **`os.getenv()` kahin bhi seedha mat call karo** — sirf `core/config.py` me. Baaki jagah
   `settings` import karo.
5. **`HTTPException` `core/` me kabhi mat raise karo.** `core/` sirf `AegisError` subclasses
   raise karega; `HTTPException` sirf `api/` me confined rahega.
6. **Audit log ka `UPDATE`/`DELETE` allow mat karo, kabhi bhi, kisi bhi reason se.** "Edit
   karna hai" lage toh naya corrective event add karo — yeh design error hai agar aisa lage.
7. **Retrieval cache ko sirf prompt pe key mat karo.** Identity include karo
   (`prompt_hash, clearance_level, sorted(departments)`), warna cross-clearance data leak
   hoga.
8. **Contract (`04_INTEGRATION_CONTRACTS.md`) khud se chupke se badalna mat** — tum author ho
   isliye zimmedari zyada hai. Koi bhi change CCR process se hi (§8), bina team ke silent edit
   nahi.

## ✅ YEH ZAROOR KARO

1. **Day 2 tak `openapi.json` + `make mock` freeze aur publish karo.** Yeh poore project ka
   sabse critical deadline hai — late hua toh M1 aur M5 dono idle baith jayenge.
2. SSE endpoint me: `X-Accel-Buffering: no`, har 15s `: keep-alive`, aur
   `await request.is_disconnected()` check karke agent task cancel karo — nahi toh har
   abandoned tab se GPU pe ek zombie generation leak hoga.
3. Har request pe ek hi `AsyncSession` (via `Depends`) — kabhi tasks ke beech share mat karo.
   Blocking calls (`bcrypt`, `libmagic`, `PyMuPDF`) `run_in_threadpool` se chalao.
4. Audit row ko `finally` block me likho — turn cancel ho ya error aaye, audit har baar record
   hona chahiye.
5. Hash-chain audit me concurrent appends ko `SELECT ... FOR UPDATE` se serialize karo, nahi
   toh do append ek saath chain fork kar sakte hain.
6. Har jagah **fail-closed**: missing claim, unparseable label, Qdrant down — sab deny, kabhi
   default-allow nahi.

## 🔗 Integration me dhyan rakhna

- Tumhara Day-2 freeze hi sabka green light hai — is din agar late ho rahe ho, sabse pehle
  channel me batao.
- Review pairing: M1↔M3, M3↔M4. Har PR jo retrieval ko touch kare, khud check karo ki
  `build_acl_filter()` uss path pe hai ya nahi.
