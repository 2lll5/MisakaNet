export async function onRequestPost(context) {
  const { env } = context;
  if (!env.MISAKANET_KV) {
    return new Response(JSON.stringify({ error: "KV not configured" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Rate limit: 3 codes per IP per 10 minutes
  const connIp = context.request.headers.get("CF-Connecting-IP") || "unknown";
  const connRateKey = `rate:connect:${connIp}`;
  const connRateRaw = await env.MISAKANET_KV.get(connRateKey, "text");
  const connRateCount = connRateRaw ? parseInt(connRateRaw, 10) || 0 : 0;
  if (connRateCount >= 3) {
    return new Response(JSON.stringify({ error: "Rate limited. Try again later." }), {
      status: 429,
      headers: { "Content-Type": "application/json" },
    });
  }
  await env.MISAKANET_KV.put(connRateKey, String(connRateCount + 1), { expirationTtl: 600 });

  // Generate 6-char alphanumeric code
  const chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let code = "";
  for (let i = 0; i < 6; i++) code += chars[Math.floor(Math.random() * chars.length)];

  // Store in KV: pending, 10 min TTL
  await env.MISAKANET_KV.put(`pair:${code}`, JSON.stringify({
    status: "pending",
    created: new Date().toISOString(),
    ip: connIp,
  }), { expirationTtl: 600 });

  return new Response(JSON.stringify({ code, expires_in: 600 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
