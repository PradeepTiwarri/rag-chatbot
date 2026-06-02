import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "../../config";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();

    const response = await fetch(`${API_BASE_URL}/api/ingest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Ingest proxy error:", error);

    return NextResponse.json(
      {
        error: "Failed to connect to backend",
      },
      {
        status: 500,
      }
    );
  }
}
