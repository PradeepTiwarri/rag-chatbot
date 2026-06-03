import { NextRequest } from "next/server";
import { API_BASE_URL } from "../../config";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { messages, video_ids } = await req.json();

  // Get the last user message
  const lastMessage = messages[messages.length - 1];
  const question = lastMessage.content;

  // Generate session ID
  const sessionId = `web_${Date.now()}_${Math.random().toString(36).substring(7)}`;

  const encoder = new TextEncoder();

  function encodeTextChunk(text: string): Uint8Array {
    const escaped = JSON.stringify(text);
    return encoder.encode(`0:${escaped}\n`);
  }

  // Helper to send citations
  function encodeCitationsChunk(citations: any[]): Uint8Array {
    return encoder.encode(`2:${JSON.stringify({ citations })}\n`);
  }

  const stream = new ReadableStream({
    async start(controller) {
      let backendResponse: Response;

      try {
        console.log("Connecting to backend:", `${API_BASE_URL}/api/chat/stream`);
        
        backendResponse = await fetch(`${API_BASE_URL}/api/chat/stream`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            session_id: sessionId,
            video_ids: video_ids || ["A", "B"],
          }),
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        console.error("Backend connection error:", msg);
        controller.enqueue(encodeTextChunk(`⚠️ Could not reach backend: ${msg}`));
        controller.close();
        return;
      }

      if (!backendResponse.ok) {
        const errText = await backendResponse.text().catch(() => "Unknown error");
        console.error("Backend error response:", backendResponse.status, errText);
        controller.enqueue(
          encodeTextChunk(`⚠️ Backend error (${backendResponse.status}): ${errText}`)
        );
        controller.close();
        return;
      }

      const reader = backendResponse.body?.getReader();
      if (!reader) {
        controller.enqueue(encodeTextChunk("⚠️ No response body from backend."));
        controller.close();
        return;
      }

      let buffer = "";
      let citationsSent = false;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += new TextDecoder().decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            try {
              const data = JSON.parse(trimmed);

              // Send citations first
              if (data.type === "citations" && !citationsSent) {
                if (data.data && Array.isArray(data.data)) {
                  controller.enqueue(encodeCitationsChunk(data.data));
                  citationsSent = true;
                }
              }
              
              // Send text tokens
              if (data.type === "token" && typeof data.data === "string") {
                controller.enqueue(encodeTextChunk(data.data));
              }
              
              // Handle errors
              if (data.type === "error") {
                controller.enqueue(
                  encodeTextChunk(`\n⚠️ ${data.data ?? "An error occurred"}`)
                );
              }
            } catch (e) {
              // Non-JSON line - skip silently
              console.debug("Failed to parse line:", trimmed);
            }
          }
        }

        // Flush any remaining buffer
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer.trim());
            if (data.type === "token" && typeof data.data === "string") {
              controller.enqueue(encodeTextChunk(data.data));
            }
          } catch {
            // ignore
          }
        }
      } catch (err) {
        console.error("Stream processing error:", err);
        controller.enqueue(encodeTextChunk("\n⚠️ Connection interrupted"));
      } finally {
        controller.close();
        reader.releaseLock();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "X-Vercel-AI-Data-Stream": "v1",
    },
  });
}
