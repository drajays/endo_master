# Endocrinology Master — Clinical Q-Bank & Notes

A static, vanilla-JS clinical Q-Bank & study portal for Endocrinology, modeled on the Harrison study app architecture. It contains chapter notes, clinically-focused MCQs, true/false statements, and assertion–reason questions.

## Sources
1. **Williams Textbook of Endocrinology (15th Edition, 2024)**
2. **Endocrine Self-Assessment Program 2021 (ESAP 2021)**
3. **Endocrine Self-Assessment Program 2015 (ESAP 2015)**

## Architecture
- `index.html` / `app.js` / `styles.css` — the entire app interface.
- `data/index.json` — the catalog containing all chapters and sections.
- `data/*.json` — chapter content files (lazy-loaded on demand).
- No build step, no framework, no backend.

## How to Run Locally
To run the app locally, serve the project folder using a local HTTP server:
```bash
python3 -m http.server 8000
```
Then navigate to `http://localhost:8000` in your web browser.
