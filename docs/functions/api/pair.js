export async function onRequestPost(context) {
  const { env, request } = context;
  if (!env.MISAKANET_KV) {
    return new Response(JSON.stringify({ error: "KV not configured" }), {
      status: 503,
      headers: { "Content-Type": "application/json" },
    });
  }

  let pairBody;
  try {
    pairBody = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const code = String(pairBody.code || "").replace(/[^A-Z0-9]/g, "").slice(0, 10);
  if (!code || code.length !== 6) {
    return new Response(JSON.stringify({ error: "Invalid code format" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const pairKey = `pair:${code}`;
  const pairData = await env.MISAKANET_KV.get(pairKey, "json");
  if (!pairData) {
    return new Response(JSON.stringify({ error: "Invalid or expired code" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (pairData.status !== "pending") {
    return new Response(JSON.stringify({ error: "Code already used" }), {
      status: 409,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Mark code as used
  pairData.status = "used";
  pairData.used_at = new Date().toISOString();
  pairData.used_ip = request.headers.get("CF-Connecting-IP") || "unknown";
  await env.MISAKANET_KV.put(pairKey, JSON.stringify(pairData), { expirationTtl: 86400 });

  // Generate short-lived token (24h)
  const tokenChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
  let token = "mcp_";
  for (let i = 0; i < 32; i++) token += tokenChars[Math.floor(Math.random() * tokenChars.length)];

  // Store token in KV for validation
  await env.MISAKANET_KV.put(`mcp_token:${token}`, JSON.stringify({
    created: new Date().toISOString(),
    expires: new Date(Date.now() + 86400000).toISOString(),
    ip: pairData.ip,
  }), { expirationTtl: 86400 });

  return new Response(JSON.stringify({ token, expires_in: 86400 }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
