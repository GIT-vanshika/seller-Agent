"use client";

import { useEffect, useState } from "react";

export default function Home() {
  const [status, setStatus] = useState<"Loading..." | "Connected" | "Disconnected">("Loading...");

  useEffect(() => {
    fetch("http://127.0.0.1:8000/health")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        if (data.status === "ok") {
          setStatus("Connected");
        } else {
          setStatus("Disconnected");
        }
      })
      .catch((err) => {
        console.error("Backend health check failed:", err);
        setStatus("Disconnected");
      });
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", textAlign: "center" }}>
      <h1>AI Purchase Confidence &amp; Deal Agent</h1>
      <p>Day 1 — Frontend Foundation</p>

      <section style={{ marginTop: "2rem", padding: "1rem", border: "1px solid #ccc", borderRadius: "8px", display: "inline-block" }}>
        <h2>Backend Status: <span style={{ color: status === "Connected" ? "green" : status === "Disconnected" ? "red" : "orange" }}>{status}</span></h2>
      </section>
    </main>
  );
}
