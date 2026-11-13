export type HealthStatus = {
  status: string;
};

function isHealthStatus(value: unknown): value is HealthStatus {
  return (
    typeof value === "object" &&
    value !== null &&
    "status" in value &&
    typeof value.status === "string"
  );
}

export async function getHealth(signal?: AbortSignal): Promise<HealthStatus> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) {
    throw new Error(`Health check failed (${response.status})`);
  }

  const body: unknown = await response.json();
  if (!isHealthStatus(body)) {
    throw new Error("Health check returned an unexpected payload");
  }
  return body;
}
