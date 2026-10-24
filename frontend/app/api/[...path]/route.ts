// Proxies /api/* from the browser to the internal FastAPI service.
//
// On Vercel the backend has no public route; this route handler reaches it over a
// service binding, which injects BACKEND_URL at runtime. Locally, without
// `vercel dev`, set BACKEND_URL in .env.local (defaults to uvicorn on :8000).
import type { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
// Song generation is queued, so every backend call is quick, but audio can take a moment.
export const maxDuration = 60;

const FORWARD_REQUEST_HEADERS = ["content-type", "accept", "range"];
const FORWARD_RESPONSE_HEADERS = ["content-type", "content-length", "content-disposition", "cache-control", "accept-ranges", "content-range"];

function backendBase(): string {
  return process.env.BACKEND_URL || "http://localhost:8000";
}

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  // The backend serves its routes under /api, the same path the browser used.
  const target = new URL(`api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`, backendBase().replace(/\/?$/, "/"));

  const headers = new Headers();
  for (const name of FORWARD_REQUEST_HEADERS) {
    const value = req.headers.get(name);
    if (value) headers.set(name, value);
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return Response.json({ detail: "Echorie is having trouble right now. Please try again in a moment." }, { status: 502 });
  }

  const out = new Headers();
  for (const name of FORWARD_RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  // Stream the body through so audio isn't buffered in this function.
  return new Response(upstream.body, { status: upstream.status, headers: out });
}

export { proxy as GET, proxy as POST };
