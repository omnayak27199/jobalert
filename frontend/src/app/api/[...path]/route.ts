import { NextRequest, NextResponse } from "next/server";

const BACKEND = (process.env.API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function proxyRequest(req: NextRequest, pathSegments: string[]) {
  const path = pathSegments.join("/");
  const target = `${BACKEND}/api/${path}${req.nextUrl.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (key === "host" || key === "connection") return;
    headers.set(key, value);
  });

  let body: BodyInit | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.arrayBuffer();
  }

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (key === "transfer-encoding") return;
    responseHeaders.set(key, value);
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
}

type RouteContext = { params: Promise<{ path: string[] }> };

async function withPath(
  req: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  const { path } = await context.params;
  return proxyRequest(req, path);
}

export async function GET(req: NextRequest, context: RouteContext) {
  return withPath(req, context);
}

export async function POST(req: NextRequest, context: RouteContext) {
  return withPath(req, context);
}

export async function PUT(req: NextRequest, context: RouteContext) {
  return withPath(req, context);
}

export async function PATCH(req: NextRequest, context: RouteContext) {
  return withPath(req, context);
}

export async function DELETE(req: NextRequest, context: RouteContext) {
  return withPath(req, context);
}
