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
          color: "#008ecf",
          marginBottom: "1.5rem",
          fontFamily: "'Open Sans', sans-serif",
        }}
      >
        About DSSC
      </h1>
      <Card
        style={{
          borderRadius: "16px",
          boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
        }}
      >
        <p
          style={{
            color: "rgba(0,142,207,0.75)",
            lineHeight: 1.8,
            marginBottom: "1rem",
            fontFamily: "'Open Sans', sans-serif",
          }}
        >
          The{" "}
          <strong style={{ color: "#008ecf" }}>
            DSSC (Data Spaces Support Centre)
          </strong>{" "}
          framework, developed by{" "}
          <a
            href="https://dssc.eu"
            target="_blank"
            rel="noreferrer"
            style={{ color: "#76b82a", textDecoration: "none" }}
          >
            DSSC
          </a>{" "}
          , defines the essential requirements for trustworthy data sharing initiatives.
        </p>
        <p
          style={{
            color: "rgba(0,142,207,0.75)",
            lineHeight: 1.8,
            marginBottom: "1rem",
            fontFamily: "'Open Sans', sans-serif",
          }}
        >
          The framework organizes requirements across 6 categories — Governance, Business, Legal, Interoperability, Control over Data &amp; Trust, and Value Creation — helping organizations understand and demonstrate
          compliance.
        </p>
        <p
          style={{
            color: "rgba(0,142,207,0.75)",
            lineHeight: 1.8,
            fontFamily: "'Open Sans', sans-serif",
          }}
        >
          This tool guides DSI leaders and Service Providers through the structured Dataspace Maturity Assessment and generates a clear
          compliance report showing where their initiative stands against the framework.
        </p>
      </Card>
    </div>
  );
}
