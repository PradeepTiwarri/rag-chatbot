import { NextRequest } from "next/server";

export const runtime = "nodejs";

export async function POST(req: NextRequest) {
  const { messages, video_ids } = await req.json();

  // Get the last user message
  const lastMessage = messages[messages.length - 1];
  const question = lastMessage.content;

  // Generate session ID (use timestamp + random)
  const sessionId = `web_${Date.now()}_${Math.random().toString(36).substring(7)}`;

  const encoder = new TextEncoder();

  /**
   * Encode a text chunk in the AI SDK Data Stream Protocol.
   * Format: `0:"<escaped-text>"\n`
   * This is what @ai-sdk/react useChat() expects.
   */
  function encodeTextChunk(text: string): Uint8Array {
    const escaped = JSON.stringify(text); // handles quotes, newlines, etc.
    return encoder.encode(`0:${escaped}\n`);
  }

  const stream = new ReadableStream({
    async start(controller) {
      let backendResponse: Response;

      try {
        backendResponse = await fetch("http://localhost:8000/api/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question,
            session_id: sessionId,
            video_ids: video_ids || ["A", "B"],
          }),
        });
      } catch (err) {
        // Network error reaching the backend
        const msg = err instanceof Error ? err.message : String(err);
        controller.enqueue(encodeTextChunk(`⚠️ Could not reach backend: ${msg}`));
        controller.close();
        return;
      }

      if (!backendResponse.ok) {
        const errText = await backendResponse.text().catch(() => "Unknown error");
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

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += new TextDecoder().decode(value, { stream: true });

          // Process complete newline-delimited JSON lines
          const lines = buffer.split("\n");
          // Keep the last (potentially incomplete) segment in the buffer
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            try {
              const data = JSON.parse(trimmed);

              if (data.type === "token" && typeof data.data === "string") {
                controller.enqueue(encodeTextChunk(data.data));
              } else if (data.type === "error") {
                controller.enqueue(
                  encodeTextChunk(`\n⚠️ ${data.data ?? "An error occurred"}`)
                );
              }
              // "citations", "start", "end" — silently ignored for now
            } catch {
              // Non-JSON line — skip silently
            }
          }
        }

        // Flush any remaining buffer content
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer.trim());
            if (data.type === "token" && typeof data.data === "string") {
              controller.enqueue(encodeTextChunk(data.data));
            }
          } catch {
            /* ignore incomplete/non-JSON tail */
          }
        }
      } finally {
        controller.close();
        reader.releaseLock();
      }
    },
  });

  return new Response(stream, {
    headers: {
      // Required content-type for @ai-sdk/react useChat() data stream protocol
      "Content-Type": "text/plain; charset=utf-8",
      "X-Vercel-AI-Data-Stream": "v1",
    },
  });
}