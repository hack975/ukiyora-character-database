# Connect this to the existing Ukiyora `/power` page

This repository is the discovery database. It is **not** the verified power-scaling calculation engine.

## Minimal server-side proxy

In the Ukiyora website, create `app/api/power/catalogue/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const base = process.env.UKIYORA_CHARACTER_API_URL;
  if (!base || !base.startsWith("https://")) {
    return NextResponse.json({ error: "Character API not configured" }, { status: 503 });
  }
  const query = (request.nextUrl.searchParams.get("q") ?? "").trim().slice(0, 120);
  if (!query) return NextResponse.json({ results: [] });
  const target = new URL("/v1/characters", base);
  target.searchParams.set("q", query);
  target.searchParams.set("limit", "24");
  try {
    const response = await fetch(target, { cache: "no-store" });
    if (!response.ok) throw new Error(`Catalogue HTTP ${response.status}`);
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: "Character catalogue temporarily unavailable" }, { status: 502 });
  }
}
```

Configure `UKIYORA_CHARACTER_API_URL` as your deployed Worker URL (or domain).

Then in the existing `components/anime-battle-lab.tsx` replace the hardcoded character search with a debounced call to `/api/power/catalogue?q=...`. Keep form selection tied to stable `character.id` and `form.id` values. A candidate form should remain **unverified** until approved in the evidence-review workflow.

Search result fields:

```json
{
  "id": "chr_333443ba9710de0e",
  "name": "Son Goku",
  "series": ["Dragon Ball (franchise)"],
  "verificationStatus": "unverified",
  "portraitUrl": null,
  "avatarUrl": "https://YOUR-API/v1/characters/chr_333443ba9710de0e/avatar.svg",
  "battleEligible": false
}
```

For character details, request `GET /v1/characters/:id`. It returns `forms` as research candidates and does not fabricate scores.

**Keep the official verdict endpoint separate:** an unverified record must return `INSUFFICIENT_VERIFIED_EVIDENCE`, not a numeric probability or a win.
