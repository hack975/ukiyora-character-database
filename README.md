# Ukiyora Character Database

**A searchable character identity + form-research catalogue for the Ukiyora Battle Lab.** The starter data includes **2,002 character-to-anime records, 67 anime groups, and 1,089 candidate form/state labels** from the supplied Ukiyora forms PDF. None of the seeds is automatically battle-verified. More character coverage requires lawful importing and ongoing research.

## What works today

- Structured JSON seed files (`data/`), reproducible SQLite FTS5 database (`data/ukiyora_characters.sqlite`), and Cloudflare D1 SQL (`db/schema.sql`, `db/seed.sql`).
- Independent character search across names and series; character detail pages can load all candidate forms.
- Branded SVG fallback avatar for **every** character. Actual copyrighted anime portraits are **not** included; there is a reviewed-image field and source/rights metadata.
- Exact source provenance and separate discovery/verified labels.
- Ready-to-deploy read-only Cloudflare Worker API with D1 binding (`src/index.ts`).
- Optional importer for larger attributed CC BY 4.0 text dataset; no bulk scraping from proprietary character APIs.
- Feats ledger table for a future reviewed power-scaling engine. No hardcoded or fabricated 1–100 attributes.

## Files

| Path | Purpose |
|---|---|
| `data/characters.json` | 2,002 names with associated series and provenance |
| `data/forms.json` | 1,089 **unverified** candidate form/state labels |
| `data/series.json` | 67 titles/groups |
| `data/ukiyora_characters.sqlite` | Searchable local sample database |
| `db/schema.sql` | Cloudflare D1-compatible schema |
| `db/seed.sql` | Data import for Cloudflare D1 |
| `src/index.ts` | Cloudflare Worker API |
| `scripts/extract_seed.py` | Reproducible extraction from user-provided PDF (requires PyMuPDF) |
| `scripts/build_database.py` | Build SQLite from JSON |
| `scripts/import_external_ccby.py` | Optional external CSV import after obtaining/verifying dataset license |
| `scripts/export_d1_seed.py` | Export current SQLite DB to D1 SQL |
| `tests/test_catalogue.py` | Database smoke tests |

## Quick local test

```bash
python scripts/build_database.py
python -m unittest discover -s tests -v
```

Search directly in SQLite:

```bash
python scripts/search.py "Son Goku"
python scripts/search.py "Naruto"
```

## Deploy to Cloudflare

You need a Cloudflare account with D1 enabled and appropriate write permission.

```bash
npm install
npx wrangler login
npx wrangler d1 create ukiyora-characters
```

Paste the new UUID in `wrangler.jsonc`, replacing the all-zero development placeholder.

```bash
npx wrangler d1 execute ukiyora-characters --local --file db/schema.sql
npx wrangler d1 execute ukiyora-characters --local --file db/seed.sql
npm run dev
```

Test `http://localhost:8787/health` and `http://localhost:8787/v1/characters?q=Goku`.

For remote deployment (after validating local):

```bash
npx wrangler d1 execute ukiyora-characters --remote --file db/schema.sql
npx wrangler d1 execute ukiyora-characters --remote --file db/seed.sql
npm run deploy
```

Protect and back up any existing production database before running migrations. For an existing Ukiyora D1 database, **merge the tables with the current migration history** rather than blindly running the above SQL. The dedicated Worker can use an independent D1 binding without replacing the existing news/manga D1 database.

## API (read only)

- `GET /health`
- `GET /v1/series`
- `GET /v1/characters?q=goku&limit=24&offset=0`
- `GET /v1/characters/:id`
- `GET /v1/characters/:id/avatar.svg`
- `GET /v1/battle/check` returns insufficient verified evidence (intentional safety guard)

Example frontend request:

```typescript
const response = await fetch(
  `${process.env.UKIYORA_CHARACTER_API_URL}/v1/characters?q=${encodeURIComponent(search)}`,
  { cache: "no-store" }
);
if (!response.ok) throw new Error("Character catalogue unavailable");
const { results } = await response.json();
```

Configure the API URL from the **server** or use a site-owned same-origin proxy. Never use a random external URL from client input.

## Extend to ~174,000 appearance records

The public [fadhilakbar anime-characters-dataset](https://huggingface.co/datasets/fadhilakbar/anime-characters-dataset) advertises 173,964 rows and a CC BY 4.0 dataset license, with character source URLs, English/Japanese names and anime associations. It does **not** provide verified transformations, feats or character portraits. Check the license and upstream rights before using it in production. Download the CSV yourself, then:

```bash
python scripts/import_external_ccby.py path/to/anime-characters-dataset.csv
python scripts/export_d1_seed.py
```

This imports names and provenance without inventing feats/forms/images and leaves cross-series identity merges for review. An appearance record may refer to a character already listed: follow an editorial merge workflow before combining them.

## Connect it to `/power`

1. Replace hardcoded-only dropdowns with `/v1/characters?q=...` (debounce and paginate).
2. Fetch `/v1/characters/:id` to display source names and form candidates.
3. Indicate candidate forms as `RESEARCH NEEDED`. Only reviewed forms from `feats_ledger` should become selectable for authoritative scoring.
4. Portraits: use `portraitUrl` when approved; otherwise show `avatarUrl`. Do not display unreviewed character art.
5. Keep the existing battle engine **separate** and require verified feats for both selected forms before it can issue a verdict. Catalogue discovery alone never qualifies a character for victory.

## Why GitHub is not the live database

GitHub is excellent for versioned catalogue source files, review and CI. It is unsuitable for high-volume per-keystroke search or mutable editorial updates. **Cloudflare D1 is the search backend**; the GitHub repository is the versioned source and deployment pipeline.

## Attribution and accuracy

See `LICENSE-NOTICE.md`. Sources must be credited, and image use independently approved. Broad character coverage ≠ verified battle data.
