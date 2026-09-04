# MEMBER 1 — Frontend · Do's & Don'ts
### Pehle `00_SABKE_LIYE_COMMON_RULES.md` padh lena. Yeh usme add hai, replace nahi.

**Tumhara area:** `frontend/**` aur `lib/types.gen.ts`. Bas. Isse bahar kuch mat chhuo.

---

## ❌ YEH MAT KARO

1. **`EventSource` use mat karo SSE ke liye.** Woh header nahi bhej sakta (Bearer token).
   `fetch` + `ReadableStream` + `TextDecoder` use karo, jaise brief me diya hai.
2. **`sources` SSE frame me `bbox` dhundhne ki koshish mat karo.** Woh field usme hoti hi nahi
   (sirf `page_start`/`page_end` hota hai). Highlight box sirf `citations` frame se milega. Yeh
   galti pehle document me thi, ab fix hai — dobara mat daalna.
3. **`lib/types.gen.ts` haath se edit mat karo.** Yeh `make types` se auto-generate hoti hai
   M3 ke OpenAPI se. Manual edit karoge toh next `make types` pe delete ho jayega.
4. **Google Fonts, CDN icon, ya koi bhi remote asset use mat karo.** Poora system air-gapped
   hai — internet off karke build test hoga. Ek bhi `https://` build output me mila toh fail.
5. **Token ko `localStorage` me mat rakho.** Sirf memory + `sessionStorage`. Aur token/document
   content console.log kabhi mat karna, dev build me bhi nahi.
6. **UI chhupa ke security mat samjho.** Kisi button/section ko sirf isliye hide karna ki
   "user ko dikhna nahi chahiye" — yeh security nahi hai, API already block karegi. Agar tumhe
   kabhi galti se koi restricted document ka title mil jaye, turant M3 ko bug report karo,
   use render mat karo.
7. **Har token pe re-render mat karo.** Poora message har naye token pe re-parse karoge toh
   ~400 tokens ke baad UI atkega. Buffer karo, ~60ms rAF tick pe flush karo.
8. **Markdown me raw HTML enable mat karo.** Document ka text untrusted hai.

## ✅ YEH ZAROOR KARO

1. `sse-parser.ts` ko **pure function** banao aur unit test likho jisme frame beech me split
   ho (network chunk boundary pe) — yeh bug ek pura din khaata hai agar test na ho.
2. Message ko Zustand me **discriminated union** se model karo, taaki late-aaya `step` frame
   already-streamed text ko overwrite na kare.
3. PDF bbox convert karte waqt yaad rakho: PDF points bottom-left origin hote hain, canvas
   CSS pixels top-left. Rotated pages (`/Rotate 90/270`) bhi handle karo.
4. Role ke hisaab se UI degrade karo (`403` aane pe graceful message, Viewer ko audit page
   dikhna hi nahi chahiye) — lekin yeh sirf UX ke liye hai, security enforcement API karti hai.
5. Mock server (`make mock`) ke against develop karo — backend ka wait mat karo.

## 🔗 Integration me dhyan rakhna

- Tumhare kaam ka sabse bada dependency: **M3 ka frozen `openapi.json` + mock server (Day 2 tak)**.
  Agar yeh late aaya, turant channel me flag karo.
- Har phase khatam hone pe M3 se apna kaam review karwao (par mapping: M1↔M3).
