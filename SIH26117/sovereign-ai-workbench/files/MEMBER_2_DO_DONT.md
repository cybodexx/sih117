# MEMBER 2 — Data Engineer · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena.

**Tumhara area:** `data_pipeline/**` (seed, eval, labels sab isi ke andar). Bas.

---

## ❌ YEH MAT KARO

1. **`clearance_level` ya `department` ke naam khud se mat banao.** Sirf yeh values chalengi:
   Clearance = `0,1,2,3` (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED),
   Department = `MAINTENANCE | OPERATIONS | SAFETY | QUALITY | ENGINEERING | ADMIN`.
   Exact spelling `04_INTEGRATION_CONTRACTS.md §1` se copy karo.
2. **`manifest.jsonl` ka schema beech me mat badlo.** M4 ka bulk-ingest script isi format
   pe depend karta hai — P1 me jo schema fix kiya, wahi poore project me chalega.
3. **Real confidential ya kisi third-party ka copyrighted data mat daalo.** Sirf public-domain,
   openly-licensed, ya khud banaya synthetic data. Har file ka licence `sources.yaml` me likho —
   judges yeh zaroor poochhte hain.
4. **Ground truth ko sirf model se generate karke final mat maano.** Ollama se draft banao,
   lekin human confirmation (CSV review queue) ke baghair kuch bhi `ground_truth.jsonl` me
   mat daalo — nahi toh recall number fake ban jayega.
5. **Random seed hatana mat, ya har run pe alag data mat banao.** Seed `42` fix rakho — agar
   demo rehearsal ka data aur stage ka data alag nikla toh live demo pe embarrassment hoga.
6. **Correlation ko 1-hop mat banao** (jaise ek hi paragraph me poora jawab likh dena) — tabhi
   "agentic" feature ka matlab hai. Kam se kam CSV+manual ya image+manual, do jagah se milna
   chahiye.

## ✅ YEH ZAROOR KARO

1. Data me jaan-boojhkar messiness rakho: operator notes me real typos/shorthand
   (`"brng temp high, tripped @0412"`), ~4% missing values, ek CSV me date format alag
   (DD-MM-YYYY vs ISO) — bilkul clean synthetic data fake dikhta hai.
2. `page` + `exact_snippet` (verbatim text) har ground-truth row me record karo — tabhi
   asli recall measure ho payega, sirf LLM se self-grade karwana kaam nahi karega.
3. 20 unanswerable-by-design questions banao — yeh system ka "abstain" feature test karta hai.
4. Adversarial RBAC set (200 prompts) me har class ke attacks daalo (direct ask, social
   engineering, cross-department probing, injection) — M3 ka poora security test isi pe chalega.
5. `seed/{public,internal,confidential,restricted}/` folder structure follow karo — yeh
   clearance level se directly maps karta hai.

## 🔗 Integration me dhyan rakhna

- Sabse pehla deadline: **Day 3 tak 20+ documents** — M4 iske baghair sirf toy PDFs pe
  test karega, real corpus pe nahi. Yeh late hua toh M4 ka kaam block hota hai.
- Har naya document ya CSV M4 ke ingest pipeline se turant test karo, sirf apne paas rakh
  ke mat baitho.
