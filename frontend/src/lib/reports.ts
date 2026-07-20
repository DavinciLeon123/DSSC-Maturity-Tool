import { api } from "./api";

/**
 * Trigger report generation for an initiative.
 * The POST endpoint scores all answers, renders the HTML report, stores it,
 * and returns the rendered HTML as text.
 */
export async function generateReport(initiativeId: number): Promise<string> {
  const res = await api.post(
    `/initiatives/${initiativeId}/report`,
    null,
    {
      responseType: "text",
      headers: { Accept: "text/html" },
    },
  );
  return res.data as string;
}

/**
 * Returns the URL for the GET report endpoint.
 * Note: this endpoint requires Bearer auth, so use generateReport() + blob URL
 * approach to open in a new tab (see questionnaire.tsx).
 */
export function getReportUrl(initiativeId: number): string {
  return `${api.defaults.baseURL}/initiatives/${initiativeId}/report`;
}
