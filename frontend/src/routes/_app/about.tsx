import { createFileRoute } from "@tanstack/react-router";
import { Card } from "antd";

export const Route = createFileRoute("/_app/about")({
  component: AboutPage,
});

function AboutPage() {
  return (
    <div style={{ maxWidth: "760px", margin: "0 auto" }}>
      <h1
        style={{
          fontSize: "1.75rem",
          fontWeight: 700,
          color: "#06004f",
          marginBottom: "1.5rem",
          fontFamily: "'Rubik', sans-serif",
        }}
      >
        About MAMI
      </h1>
      <Card
        style={{
          borderRadius: "16px",
          boxShadow: "0 2px 12px rgba(6,0,79,0.06)",
        }}
      >
        <p
          style={{
            color: "rgba(6,0,79,0.75)",
            lineHeight: 1.8,
            marginBottom: "1rem",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          The{" "}
          <strong style={{ color: "#06004f" }}>
            MAMI (Minimal Agreements for Maximal Interoperability)
          </strong>{" "}
          framework, developed by{" "}
          <a
            href="https://coe-dsc.nl"
            target="_blank"
            rel="noreferrer"
            style={{ color: "#399e5a", textDecoration: "none" }}
          >
            CoE-DSC
          </a>{" "}
          , defines the essential requirements for trustworthy data sharing initiatives.
        </p>
        <p
          style={{
            color: "rgba(6,0,79,0.75)",
            lineHeight: 1.8,
            marginBottom: "1rem",
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          The framework organizes requirements across a 4×3 matrix covering governance, technical,
          legal, and operational dimensions — helping organizations understand and demonstrate
          compliance.
        </p>
        <p
          style={{
            color: "rgba(6,0,79,0.75)",
            lineHeight: 1.8,
            fontFamily: "'Rubik', sans-serif",
          }}
        >
          This tool guides DSI leaders and Service Providers through the structured questionnaire and generates a clear
          compliance report showing where their initiative stands against the framework.
        </p>
      </Card>
    </div>
  );
}
