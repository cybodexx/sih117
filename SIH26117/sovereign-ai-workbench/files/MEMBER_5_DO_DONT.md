# MEMBER 5 — Agentic Workflow Engineer · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena.

**Tumhara area:** `backend/agents/**` (isi ke andar `backend/agents/tools/` bhi aata hai —
alag top-level `backend/tools/` folder NAHI banana, woh galti pehle brief me thi, ab fix hai).
`eval/router_eval.py` bhi tumhara. `backend/services/llm/prompts.py` sirf yeh ek file M6 ke
folder me tumhara likha hua hai (carve-out hai, poora folder nahi).

---

## ❌ YEH MAT KARO

1. **`acl_filter` ko `agents/` ya `tools/` ke andar khud se construct mat karo.** Hamesha
   sealed state se aana chahiye (M3/M4 ka banaya hua). Agent ko apni access khud badhane ka
   koi rasta nahi hona chahiye.
2. **ReAct loop ko unbounded mat chhodo.** Iterations, tool calls, wall-clock time, aur
   `recursion_limit` — sab hard-capped code me hone chahiye, sirf prompt me "please stop"
   likhna kaafi nahi hai.
3. **In-memory interrupt/state use mat karo HITL ke liye.** Process restart ya browser
   refresh pe woh mar jayega. Postgres checkpointer (`AsyncPostgresSaver`) + stable
   `thread_id = session_id` use karo.
4. **Retrieved text (corpus se aaya) ko kabhi tool-call trigger karne do mat.** Yeh
   attacker-controlled ho sakta hai (prompt injection). `<untrusted_data>` wrapping karo,
   retrieval hops pe tool binding disable rakho.
5. **Model output ko kabhi `exec` mat karo NL→SQL ke liye.** Parse + validate: single
   statement, `SELECT` only, allowlisted tables, mandatory `LIMIT`, aur read-only DB role
   backstop ki tarah.
6. **Groundedness/coverage ko LLM se "kaisa laga" pooch ke measure mat karo.** Mechanically
   check karo — har factual sentence ke saath citation hai ya nahi.
7. **`backend/tools/vector_search.py` jaisa top-level path mat banao.** Sahi path
   `backend/agents/tools/vector_search.py` hai (master repo structure se match karta hai).

## ✅ YEH ZAROOR KARO

1. Structured output force karo routing ke liye (Pydantic `RouteDecision`) — chhota 8B model
   free-text classifier ki tarah use karna weak hoga. Deterministic overrides pehle, lexical
   prior fuse karo, confidence floor se neeche safest route pe default karo.
2. Refresh mid-approval ke baad bhi resume sahi se ho, isko test karo — `aupdate_state` +
   `astream(None, cfg)`.
3. Abstain hone pe answer ko competent lage aisa likho: "documents me nahi hai, closest
   related section X hai, clearance Y chahiye" — yeh guess se behtar hai.
4. **P1 float duty:** ek agent mock banao jo realistic `step`/`sources`/`token`/`citations`
   sequence emit kare, taaki M1 apna poora trace UI Day 2 se hi bina real agent ke bana sake.

## 🔗 Integration me dhyan rakhna

- Sabse bhaari phase tumhari hai (P4, 8 points) — M4 ka `vector_search` retriever Day 6 tak
  chahiye hoga, aur M2 ka corpus/labels bhi. Dono late hue toh flag karo turant.
- Review pairing: M4↔M5, M5↔M6.
