import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const { messages, video_ids } = await req.json();
  
  // Get the last user message
  const lastMessage = messages[messages.length - 1];
  const question = lastMessage.content;
  
  // Generate session ID (use timestamp + random)
  const sessionId = `web_${Date.now()}_${Math.random().toString(36).substring(7)}`;
  
  // Call FastAPI backend
  const response = await fetch("http://localhost:8000/api/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: question,
      session_id: sessionId,
      video_ids: video_ids || ["A", "B"],
    }),
  });
  
  // Create a ReadableStream to forward the response
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      const reader = response.body?.getReader();
      if (!reader) {
        controller.close();
        return;
      }
      
      let fullAnswer = "";
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          const chunk = new TextDecoder().decode(value);
          const lines = chunk.split("\n");
          
          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                
                if (data.type === "citations") {
                  // Store citations for later
                  continue;
                } else if (data.type === "token") {
                  fullAnswer += data.data;
                  controller.enqueue(encoder.encode(data.data));
                } else if (data.type === "error") {
                  controller.enqueue(encoder.encode(`[Error: ${data.data}]`));
                }
              } catch (e) {
                // Not JSON, pass through
                controller.enqueue(encoder.encode(line));
              }
            }
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
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}