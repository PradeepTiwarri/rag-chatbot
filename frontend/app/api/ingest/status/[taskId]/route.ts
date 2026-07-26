import { NextRequest, NextResponse } from "next/server";
import { API_BASE_URL } from "../../../../config";

export const runtime = "nodejs";

export async function GET(
  req: NextRequest,
  { params }: { params: { taskId: string } }
) {
  try {
    const { taskId } = params;

    const response = await fetch(
      `${API_BASE_URL}/api/ingest/status/${taskId}`,
      { method: "GET" }
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Ingest status proxy error:", error);

    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}
