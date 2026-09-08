# SABKE LIYE — Common Rules (pehle yeh padho, phir apna wala file)
### SIH26117 · Team ke liye ek hi message · v1.0

Yeh file sabko forward karo. Isme woh rules hain jo **har member** pe laagu hote hain — inko
todne se poori team ka integration phase (P6) toot sakta hai.

---

## 1. Sabse important rule: apne folder se bahar mat jao

Har member ka apna alag folder hai (`frontend/`, `data_pipeline/`, `backend/core+api+db`,
`backend/services/rag+ingest`, `backend/agents`, `docker-compose+Makefile`). Poori list
`00_MASTER_SRS.md §8` (Repository Structure) me hai.

- **Apne folder ke bahar ek line bhi mat likho.** Kisi doosre ka file edit karna hai (chahe
  1-line typo fix ho) → khud mat karo, unko batao ya PR bhejo unke review ke saath.
- Agar do member ek hi jagah kaam karte lag rahe hain (jaise `backend/services/llm/prompts.py` —
  yeh M5 likhega par folder M6 ka hai), toh woh **jaan-boojhkar** carve-out hai, docs me likha
  hua hai. Confusion ho toh pehle poochho, guess mat karo.

## 2. Contract file (`04_INTEGRATION_CONTRACTS.md`) BIBLE hai

- Field ka naam, JSON shape, endpoint path — **copy-paste karo, yaad se mat likho.**
  `page_start` hai, `page` nahi. Agar contract me field nahi hai (jaise `sources` frame me
  `bbox_union` nahi hai), toh apne code me bhi mat maano ki woh aayega.
- Contract me kuch galat lag raha hai ya missing hai → **khud change mat karo.** CCR process
  follow karo (`04_INTEGRATION_CONTRACTS.md §8`): issue kholo → sab 6 members ki approval →
  version bump → same din sab mocks update. Ek chuppi se kiya gaya change poori team ka kaam
  todta hai.
- Day 2 ke baad contract "frozen" hai. Day 12 ke baad Lead (M6) ki sign-off chahiye. Day 15 ke
  baad bilkul freeze — bug ko implementation me fix karo, contract me nahi.

## 3. Chhoti file, chhota function — yeh CI khud check karega

- **300 lines se zyada ek file nahi.** 50 lines se zyada ek function nahi. CI red ho jayega
  (`tools/check_loc.py`, M6 ne banaya hai) — file badi ho rahi hai toh Day 1 se hi split karo,
  last moment pe mat chhodo.
- Har function pe type hints (`mypy` / TypeScript `strict` dono clean hone chahiye).
- Koi bhi `any` (TS) ya bare `except:` (Python) allowed nahi hai.

## 4. Security — yeh sabki zimmedari hai, sirf M3 ki nahi

- Koi bhi endpoint, tool, ya query **client se aaye hue filter/clearance/department field ko
  kabhi trust mat karo.** Sirf JWT se aayi identity trust hoti hai. Yeh rule tootne se poora
  RBAC demo fail ho jata hai.
- Kisi bhi log line me password, token, ya document ka actual content kabhi mat likho.
- Kuch bhi missing/unclear ho (label, permission, config) → **deny karo, allow mat karo.**
  "Fail closed" — kabhi bhi default allow nahi.

## 5. Har cheez `docker compose up` ke andar chalni chahiye

Sirf apne laptop pe `npm run dev` ya `uvicorn` se chalna "done" nahi maana jayega. Roz ka
integration smoke test (`make up && make smoke`) green hona chahiye — apna kaam push karne se
pehle khud ek baar chala ke dekho.

## 6. Communication

- Roz 15-min sync me batao: kya complete hua, kya block hai, kaunsa contract change hua.
- **2 ghante se zyada block ho toh turant channel me bolo.** Chup baithne se pura ek phase
  team ka waste hota hai — koi inaam nahi milta chup rehne ka.
- Apna PR merge karne se pehle apne review-partner se review karwao (pairing already fixed hai:
  M1↔M3, M3↔M4, M4↔M5, M5↔M6, M6↔M1, M2↔M4). Khud apna PR merge mat karo.

---

Ab apna wala file kholo:
`MEMBER_1_DO_DONT.md` · `MEMBER_2_DO_DONT.md` · `MEMBER_3_DO_DONT.md` ·
`MEMBER_4_DO_DONT.md` · `MEMBER_5_DO_DONT.md` · `MEMBER_6_DO_DONT.md`
