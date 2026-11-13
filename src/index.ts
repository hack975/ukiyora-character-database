/** Public read-only catalogue API for Cloudflare Worker + D1.
 * IMPORTANT: discovery data is not canon-verified combat data.
 */
export interface Env {
  DB: D1Database;
  ALLOWED_ORIGINS?: string;
}

type CharacterRow = {
  id: string;
  name: string;
  japanese_name: string | null;
  aliases_json: string;
  profile_status: string;
  portrait_url: string | null;
  portrait_source_url: string | null;
  portrait_credit: string | null;
  portrait_license: string | null;
  portrait_status: string;
  source_kind: string;
  series_names?: string | null;
};

const DEFAULT_ORIGINS = ["https://ukiyora.com", "https://www.ukiyora.com", "http://localhost:3000"];
const json = (body: unknown, status = 200, headers?: HeadersInit) => {
  const responseHeaders = new Headers({
    "content-type": "application/json; charset=utf-8",
    "cache-control": "public, max-age=60",
  });
  if (headers) new Headers(headers).forEach((value, key) => responseHeaders.set(key, value));
  return new Response(JSON.stringify(body), { status, headers: responseHeaders });
};

function clamp(value: string | null, fallback: number, min: number, max: number): number {
  const n = value == null ? fallback : Number(value);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, Math.floor(n))) : fallback;
}
function ftsQuery(value: string): string | null {
  const words = value.normalize("NFKC").match(/[\p{L}\p{N}]+/gu)?.slice(0, 8) ?? [];
  if (!words.length) return null;
  return words.map((word) => `"${word}"*`).join(" AND ");
}
function initials(text: string): string {
  return text.trim().split(/\s+/).slice(0, 2).map((p) => [...p][0] ?? "").join("").toUpperCase().slice(0, 3);
}
function escapeXml(value: string): string {
  return value.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;" }[c]!));
}
function sanitizedCharacter(row: CharacterRow, origin: string) {
  const photo = row.portrait_status === "approved" && row.portrait_url?.startsWith("https://") ? row.portrait_url : null;
  return {
    id: row.id,
    name: row.name,
    japaneseName: row.japanese_name,
    aliases: JSON.parse(row.aliases_json),
    series: row.series_names?.split(" | ").filter(Boolean) ?? [],
    verificationStatus: row.profile_status,
    portraitUrl: photo,
    portraitCredit: photo ? row.portrait_credit : null,
    avatarUrl: `${origin}/v1/characters/${encodeURIComponent(row.id)}/avatar.svg`,
    hasApprovedPortrait: Boolean(photo),
    // The character's presence in the catalogue is NEVER evidence of fight readiness.
    battleEligible: false,
    sourceKind: row.source_kind,
  };
}
function allowedOrigins(env: Env): string[] {
  return env.ALLOWED_ORIGINS?.split(",").map((s) => s.trim()).filter(Boolean) ?? DEFAULT_ORIGINS;
}
const characterSelect = `SELECT c.*, (
  SELECT group_concat(name, ' | ') FROM (
    SELECT s.name AS name FROM appearances a JOIN series s ON s.id=a.series_id
    WHERE a.character_id=c.id ORDER BY s.name
  )
) AS series_names FROM characters c`;

async function route(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (request.method !== "GET") return json({ error: "Method not allowed" }, 405, { Allow: "GET" });

  if (path === "/health") {
    const counts = await env.DB.prepare(`SELECT
      (SELECT COUNT(*) FROM series) AS series,
      (SELECT COUNT(*) FROM characters) AS characters,
      (SELECT COUNT(*) FROM character_forms) AS formCandidates,
      (SELECT COUNT(*) FROM feats_ledger WHERE verification_status='verified') AS verifiedFeats`).first();
    return json({ ok: true, catalogue: counts });
  }

  if (path === "/v1/series") {
    const limit = clamp(url.searchParams.get("limit"), 100, 1, 300);
    const rows = await env.DB.prepare(`SELECT s.id,s.name,COUNT(a.character_id) AS characterCount
      FROM series s LEFT JOIN appearances a ON a.series_id=s.id
      GROUP BY s.id ORDER BY s.name LIMIT ?`).bind(limit).all();
    return json({ results: rows.results });
  }

  if (path === "/v1/characters") {
    const input = (url.searchParams.get("q") ?? "").trim().slice(0, 120);
    const q = ftsQuery(input);
    if (!q) return json({ results: [], count: 0, query: input, warning: "Provide a character or series search term" });
    const limit = clamp(url.searchParams.get("limit"), 24, 1, 50);
    const offset = clamp(url.searchParams.get("offset"), 0, 0, 100_000);
    const result = await env.DB.prepare(`${characterSelect}
      JOIN character_search_fts f ON f.character_id=c.id
      WHERE character_search_fts MATCH ?
      ORDER BY bm25(character_search_fts),c.name
      LIMIT ? OFFSET ?`).bind(q, limit, offset).all<CharacterRow>();
    const count = await env.DB.prepare(`SELECT COUNT(*) AS count FROM character_search_fts
      WHERE character_search_fts MATCH ?`).bind(q).first<{count:number}>();
    return json({ query: input, count: count?.count ?? 0, limit, offset,
      results: result.results.map((r) => sanitizedCharacter(r, url.origin)) });
  }

  const avatar = /^\/v1\/characters\/([a-zA-Z0-9_-]+)\/avatar\.svg$/.exec(path);
  if (avatar) {
    const found = await env.DB.prepare("SELECT name FROM characters WHERE id=?").bind(avatar[1]).first<{name:string}>();
    if (!found) return json({error:"Character not found"},404);
    const monogram = escapeXml(initials(found.name));
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 480" role="img" aria-label="Ukiyora character placeholder"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#171220"/><stop offset="1" stop-color="#37202a"/></linearGradient></defs><rect width="360" height="480" fill="url(#g)"/><circle cx="180" cy="200" r="99" fill="#292031" stroke="#ff6846" stroke-width="3"/><text x="180" y="219" font-family="system-ui, sans-serif" font-size="75" font-weight="700" text-anchor="middle" fill="#f7f4ee">${monogram}</text><text x="180" y="409" font-family="system-ui, sans-serif" font-size="23" text-anchor="middle" fill="#ff6846">UKIYORA</text></svg>`;
    return new Response(svg, {headers:{"content-type":"image/svg+xml; charset=utf-8","cache-control":"public, max-age=86400","x-content-type-options":"nosniff"}});
  }

  const detail = /^\/v1\/characters\/([a-zA-Z0-9_-]+)$/.exec(path);
  if (detail) {
    const found = await env.DB.prepare(`${characterSelect} WHERE c.id=?`).bind(detail[1]).first<CharacterRow>();
    if (!found) return json({error:"Character not found"},404);
    const forms = await env.DB.prepare(`SELECT id,label,kind,continuity,arc,verification_status AS verificationStatus,source_ref AS sourceRef
      FROM character_forms WHERE character_id=? ORDER BY sort_order,label`).bind(detail[1]).all();
    return json({ ...sanitizedCharacter(found, url.origin), forms: forms.results });
  }

  if (path === "/v1/battle/check") {
    return json({ outcome: "INSUFFICIENT_VERIFIED_EVIDENCE", canIssueVerdict: false,
      reason: "This catalogue supplies identities and form candidates, not verified combat scores. Use the Ukiyora reviewed-feats engine." }, 409);
  }

  return json({ error: "Not found", endpoints: ["/health", "/v1/series", "/v1/characters?q=goku", "/v1/characters/:id"] }, 404);
}
export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const origin = request.headers.get("Origin");
    const allowed = origin && allowedOrigins(env).includes(origin) ? origin : null;
    try {
      const result = await route(request, env);
      if (allowed) {
        result.headers.set("access-control-allow-origin", allowed);
        result.headers.set("vary", "Origin");
      }
      result.headers.set("x-content-type-options", "nosniff");
      return result;
    } catch (err) {
      console.error("catalogue-api", err instanceof Error ? err.message : "unknown error");
      return json({ error: "Catalog service unavailable" }, 500, { "cache-control": "no-store" });
    }
  },
};
