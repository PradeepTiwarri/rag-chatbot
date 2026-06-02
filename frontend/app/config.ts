export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.VITE_API_URL ||
  "http://localhost:8000";

if (typeof window !== "undefined") {
  console.log("API_BASE_URL (Client) =", API_BASE_URL);
} else {
  console.log("API_BASE_URL (Server) =", API_BASE_URL);
}
