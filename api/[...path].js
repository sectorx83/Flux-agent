/**
 * Same-origin relay from the Vercel dashboard to the private Flux host.
 * Configure FLUX_API_URL as a Vercel environment variable (HTTPS URL).
 * Browser authorization is forwarded; credentials are never stored here.
 */
const ALLOWED = /^(health|tasks(?:\/\d+(?:\/stream)?)?|devices(?:\/pair|\/[^/]+)?|workflows\/events\/[A-Za-z0-9_.-]+)$/;

module.exports = async function handler(req, res) {
  const base = process.env.FLUX_API_URL;
  if (!base) {
    res.status(503).json({ detail: "Flux host is not configured. Set FLUX_API_URL in Vercel." });
    return;
  }

  const rawPath = Array.isArray(req.query.path) ? req.query.path.join("/") : "";
  if (!ALLOWED.test(rawPath)) {
    res.status(404).json({ detail: "Unknown Flux API route." });
    return;
  }

  let target;
  try {
    const parsed = new URL(base);
    if (parsed.protocol !== "https:" || parsed.username || parsed.password) throw new Error();
    target = new URL("/" + rawPath, parsed.origin);
  } catch {
    res.status(500).json({ detail: "FLUX_API_URL must be a valid HTTPS origin." });
    return;
  }

  const method = req.method || "GET";
  if (!["GET", "POST", "DELETE"].includes(method)) {
    res.status(405).setHeader("Allow", "GET, POST, DELETE");
    res.end();
    return;
  }

  const headers = {};
  for (const name of ["authorization", "content-type", "accept", "last-event-id"]) {
    if (req.headers[name]) headers[name] = req.headers[name];
  }

  try {
    const body = method === "POST" ? await new Promise((resolve, reject) => {
      const chunks = [];
      req.on("data", chunk => chunks.push(chunk));
      req.on("end", () => resolve(Buffer.concat(chunks)));
      req.on("error", reject);
    }) : undefined;

    const upstream = await fetch(target, {
      method,
      headers,
      body,
      signal: AbortSignal.timeout(65000)
    });

    res.statusCode = upstream.status;
    for (const name of ["content-type", "cache-control", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) res.setHeader(name, value);
    }
    res.setHeader("X-Content-Type-Options", "nosniff");

    if (!upstream.body) {
      res.end();
      return;
    }
    for await (const chunk of upstream.body) res.write(Buffer.from(chunk));
    res.end();
  } catch (error) {
    if (!res.headersSent) res.status(502).json({ detail: "Flux host is unreachable. Check its HTTPS tunnel and FLUX_API_URL." });
    else res.end();
  }
};
