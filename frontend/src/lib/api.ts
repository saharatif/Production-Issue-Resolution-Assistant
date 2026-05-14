export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function sensorStreamUrl(scenario: string) {
  const url = new URL("/stream/sensor", API_BASE_URL);
  url.searchParams.set("scenario", scenario);
  return url.toString();
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(new URL(path, API_BASE_URL), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(new URL(path, API_BASE_URL));
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function reportPdfUrl(issueId: string) {
  return new URL(`/api/reports/${issueId}/pdf`, API_BASE_URL).toString();
}
