# Rakuten Ichiba API – Developer Notes

## Why web search finds RTX 5090 but API sometimes returns 0 results

The **mall search page** (https://search.rakuten.co.jp/search/mall/RTX+5090/) searches the **whole mall** with no genre filter.  
The **Ichiba Item Search API** in this project was using **genreId=100081** (グラフィックボード) only. New or some listings may be categorized under a different genre, or the genre index may lag, so the API returns 0 items while the web shows many.

**Current behavior:**  
1. First request uses `genreId=100081` (graphics board).  
2. If the API returns **0 results**, we retry **without** `genreId` (whole-mall search, same scope as the web).  
3. Results are then filtered so that the product name contains the keyword (e.g. "RTX 5090"), to avoid irrelevant hits.

So RTX 5090 and similar keywords can be collected even when the genre-limited search returns nothing.

**CPU/RAM/SSD/主板 returning "0 results from API":**
Root cause: The 2022 API uses `sort=+itemPrice` with `hits=30`. Without `minPrice`, cheap accessories that mention the CPU name (coolers, thermal paste, "Ryzen 7 9800X3D 対応") fill all 30 result slots. After the Python-level min_price filter, 0 results remain. The fallback genre (100081 = GPU) also returns 0 CPUs.

**Fix (applied):** Pass `minPrice` to the API on the whole-mall search so cheap accessories are excluded at the API level. The 30 returned items will include actual CPUs/RAM/SSDs priced above the threshold.

## HTTP 400 wrong_parameter (e.g. "RTX 4090 D")

**Symptom:** Search with keyword `RTX 4090 D` returns `Rakuten API HTTP 400: wrong_parameter`.

**Current behavior:** Collection skips the failing keyword and continues with the rest. Skipped keywords are reported at the end (dashboard: "采集完成。跳过 n 个: RTX 4090 D (...)").

**Root cause confirmed:**

The Rakuten 2022 API rejects any keyword that contains a **standalone single-character token** (one character surrounded by spaces). This includes:
- Trailing single letter: `"RTX 4090 D"` (the "D")
- Middle single digit: `"Ryzen 9 9900X"` (the "9"), `"Core Ultra 5 225F"` (the "5")

All `Ryzen 5/7/9 ...` and `Core Ultra 5/7/9 ...` keywords trigger this.

**Fix (applied):** `_sanitize_keyword()` now removes middle standalone single digits. On `wrong_parameter`, the code retries with the sanitized keyword automatically.

**Possible causes (for investigation, historical):**

1. **Keyword format**
   Rakuten 2022 API requires UTF-8 encoded keyword; length limits and character rules may apply. A trailing space or the pattern "4090 D" might trigger validation.

2. **Try variants**  
   - `RTX 4090D` (no space)  
   - `RTX 4090 D` (current)  
   - Or remove this keyword from seed and use "RTX 4090" only.

3. **API docs**  
   - [Ichiba Item Search 2022](https://webservice.rakuten.co.jp/documentation/ichiba-item-search)  
   - 400 wrong_parameter: check parameter encoding, length, and allowed characters.

4. **Legacy API**  
   The legacy Ichiba API (numeric Application ID) may accept the same keyword; we fall back to it on 503, not on 400. If 2022 API consistently rejects "RTX 4090 D", consider calling the legacy API for this keyword only.

**Workaround:** Rename the keyword in Admin to `RTX 4090D` (no space) and re-run collection; if it still fails, remove or leave skipped.
