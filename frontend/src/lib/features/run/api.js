const apiBase = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function startRun(prompt) {
  const response = await fetch(`${apiBase}/api/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  return response.json();
}

export function createEventSource(runId) {
  return new EventSource(`${apiBase}/api/events/${runId}`);
}

export async function fetchRun(runId) {
  const response = await fetch(`${apiBase}/api/runs/${runId}`);
  return response.json();
}

export async function fetchReport(runId) {
  const response = await fetch(`${apiBase}/api/artifacts/${runId}/report.md`);
  return response.blob();
}
