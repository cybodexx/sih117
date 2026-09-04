# MEMBER 4 — AI & RAG Engineer · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena.

**Tumhara area:** `backend/services/ingest/`, `backend/services/rag/`, `backend/worker/`,
`eval/{rag_eval,ingest_bench}.py`.

---

## ❌ YEH MAT KARO

1. **CSV rows ko kabhi embed mat karo.** Vector precision kharab hoti hai aur aggregate
   nahi ho sakta. Data card + per-entity slices banao; row-level sawaal SQL (M5 ka tool)
   se answer honge.
2. **`search()` function me `filter` ya `clearance` parameter mat add karo.** Contract
   (`§6.1`) me jaan-boojhkar yeh signature me nahi hai — koi tool apni access khud badha na
   sake, isliye. Yeh add kiya toh security model toot jayega.
3. **Fixed-size chunking mat karo (bas character count se todna).** Isse warning apne
   procedure se, torque value apni unit se alag ho jata hai. Headings respect karo, table ko
   atomic rakho, heading breadcrumb carry karo.
4. **Bade table (300 rows) ko ek chunk ya 300 context-less fragments mat banao.** Rows split
   karo aur har fragment me header repeat karo.
5. **OCR vs native text ka decision poore document pe mat lo — per-page lo.** Kuch pages
   scan hote hain, kuch native, kuch "broken" text layer (ligature garbage) — `alpha_ratio`
   guard use karo.
6. **Re-ingest pe idempotency mat bhoolna.** `uuid5(document_id + chunk_index)` point ids use
   karo aur re-ingest se pehle `document_id` se purane delete karo — nahi toh ek retry se
   corpus double ho jayega aur retrieval quality chupke se kharab ho jayegi.
7. **Reranker ko 100 candidates pe mat chalao.** 20 tak thik hai; zyada hua toh latency mar
   jayegi — `ENABLE_RERANKER` flag rakho Profile-C hardware ke liye.

## ✅ YEH ZAROOR KARO

1. Qdrant payload indexes (`clearance_level`, `department`, `document_id`, `status`) **migration
   script se banao**, haath se nahi — ACL pre-filter isi pe depend karta hai.
2. Hybrid search: dense + BM25 sparse + Reciprocal Rank Fusion. Exact codes/part-numbers
   ("SKF-6206-2RS", "E-4471") pe dense search fail karta hai, BM25 jeetega — hybrid non-optional
   hai industrial corpus ke liye.
3. `build_acl_filter()` ko **har** search call pe pre-filter ki tarah lagao (post-filter nahi) —
   M3 ke saath `acl_reverify()` bhi wire karo taaki re-labelled documents turant reflect ho.
4. Chunk payload contract Day 3 tak M3/M5 ke saath freeze karo — yeh unka blocker hai.

## 🔗 Integration me dhyan rakhna

- Tumhara retriever (`vector_search`) Day 6 tak ready hona chahiye — M5 ka sabse bhaari phase
  (P4) isi pe start hota hai. Late hua toh M5 ka poora agentic kaam late shuru hoga.
- Review pairing: M2↔M4 (data), M4↔M5 (agent tools).
