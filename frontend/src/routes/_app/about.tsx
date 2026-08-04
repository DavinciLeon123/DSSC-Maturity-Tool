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
          color: "#1c2025",
          marginBottom: "1.5rem",
          fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
        }}
      >
        About Data Space Maturity Assessment Tool
      </h1>
      <Card
        style={{
          borderRadius: "16px",
          boxShadow: "0 2px 12px rgba(0,142,207,0.06)",
        }}
      >
        <p
          style={{
            color: "#3d444b",
            lineHeight: 1.8,
            marginBottom: "1rem",
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          }}
        >
          The Data Space Maturity Assessment Tool helps data space architects and business leaders evaluate the maturity of their data space initiatives using the CEN/CLC/TS 18331:2026 standard.
        </p>
        <p
          style={{
            color: "#3d444b",
            lineHeight: 1.8,
            fontFamily: "'Jost', 'Helvetica Neue', Arial, sans-serif",
          }}
        >
          Co-created by the Dutch Centre of Excellence for Data Sharing and Cloud and the European Data Spaces Support Centre, this free self-assessment provides a maturity profile, highlights strengths and improvement areas, and helps value coaches and initiatives establish a baseline for measuring progress and guiding future development.
        </p>
      </Card>
    </div>
  );
}
