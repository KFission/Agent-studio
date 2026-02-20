"use client";

export default function ErrorBoundary({ error, reset }) {
  return (
    <div style={{ padding: 40, fontFamily: "system-ui, sans-serif" }}>
      <h2 style={{ color: "#c00", marginBottom: 8 }}>Client-side Error</h2>
      <pre style={{ background: "#f5f5f5", padding: 16, borderRadius: 8, overflow: "auto", fontSize: 13, whiteSpace: "pre-wrap", maxHeight: 400 }}>
        {error?.message}
        {"\n\n"}
        {error?.stack}
      </pre>
      <button onClick={reset} style={{ marginTop: 16, padding: "8px 16px", cursor: "pointer" }}>
        Try Again
      </button>
    </div>
  );
}
