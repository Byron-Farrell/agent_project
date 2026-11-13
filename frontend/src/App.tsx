import { useEffect, useState } from "react";
import { getHealth, type HealthStatus } from "./api/client";

export function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((result) => {
        setHealth(result);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setHealth(null);
        setError(caught instanceof Error ? caught.message : "Health check failed");
      });

    return () => controller.abort();
  }, []);

  return (
    <main>
      <h1>Agent project</h1>
      <p>API health from <code>/api/health</code></p>
      {health ? <p role="status">status: {health.status}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      {!health && !error ? <p>Checking the API…</p> : null}
    </main>
  );
}
