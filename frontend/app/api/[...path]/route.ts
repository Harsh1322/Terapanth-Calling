const flaskApiUrl = process.env.FLASK_API_URL || "http://127.0.0.1:5000";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyToFlask(request: Request, context: RouteContext) {
  const { path } = await context.params;
  const incomingUrl = new URL(request.url);
  const apiOrigin = new URL(flaskApiUrl).origin;
  const upstreamUrl = new URL(
    `/api/${path.map(encodeURIComponent).join("/")}${incomingUrl.search}`,
    apiOrigin,
  );

  const headers = new Headers(request.headers);
  headers.delete("connection");
  headers.delete("content-length");
  headers.delete("host");
  headers.delete("transfer-encoding");
  headers.set("referer", `${apiOrigin}/`);

  const hasBody = !["GET", "HEAD"].includes(request.method.toUpperCase());
  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined,
    cache: "no-store",
    redirect: "manual",
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    const header = key.toLowerCase();
    if (
      ![
        "connection",
        "content-encoding",
        "content-length",
        "keep-alive",
        "proxy-connection",
        "set-cookie",
        "transfer-encoding",
        "upgrade",
      ].includes(header)
    ) {
      responseHeaders.set(key, value);
    }
  });
  const getSetCookie = (
    upstream.headers as Headers & { getSetCookie?: () => string[] }
  ).getSetCookie;
  const cookies = getSetCookie?.call(upstream.headers) ?? [];
  for (const cookie of cookies) responseHeaders.append("set-cookie", cookie);

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxyToFlask;
export const HEAD = proxyToFlask;
export const POST = proxyToFlask;
export const PUT = proxyToFlask;
export const PATCH = proxyToFlask;
export const DELETE = proxyToFlask;
export const OPTIONS = proxyToFlask;
