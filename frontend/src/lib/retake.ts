import { useNavigate } from "@tanstack/react-router";
import { Modal } from "antd";
import { api } from "./api";

interface InitiativeStatus {
  id: number;
  status: string;
}

/**
 * D-13/D-14: shared entry point for "start or retake the assessment" — the
 * single source of truth for the confirm-before-retake UX (bug #1 fix).
 * Any UI surface that can navigate a user into /questionnaire (Dashboard
 * CTA, TopNav nav-drawer item, future entry points) MUST route through this
 * hook rather than rendering a bare <Link to="/questionnaire">, so a
 * submitted initiative is never silently left un-retaken — the underlying
 * POST /initiatives/{id}/retake contract is already correct and tested
 * (backend/tests/api/test_retake_flow.py); this hook only wires the
 * frontend up to it consistently everywhere.
 *
 * Fetches the caller's current initiative fresh on every call (not cached
 * component state) so the confirm-or-skip decision always reflects live
 * server-side status, regardless of which component invokes it.
 */
export function useStartOrRetakeAssessment(onError?: (message: string) => void) {
  const navigate = useNavigate();

  return async function startOrRetakeAssessment(): Promise<void> {
    let initiative: InitiativeStatus;
    try {
      const res = await api.get<InitiativeStatus>("/initiatives/me");
      initiative = res.data;
    } catch {
      // No initiative registered yet, or a transient fetch failure — land on
      // Dashboard, which already renders the registration flow / its own
      // error state, rather than a wizard this hook cannot gate correctly.
      navigate({ to: "/dashboard" });
      return;
    }

    if (initiative.status === "submitted") {
      Modal.confirm({
        title: "Start a new assessment?",
        content:
          "This creates a new, permanent version in your history. Your previous submitted assessment stays unchanged, and you'll answer all 52 questions again from scratch — nothing carries over.",
        okText: "Start new assessment",
        cancelText: "Cancel",
        onOk: async () => {
          try {
            await api.post(`/initiatives/${initiative.id}/retake`);
            navigate({ to: "/questionnaire" });
          } catch {
            onError?.("Could not start a new assessment. Please try again.");
            // antd Modal.confirm keeps the dialog open when onOk's promise
            // rejects — re-throw so a failed retake never navigates into a
            // still-locked questionnaire.
            throw new Error("retake failed");
          }
        },
      });
      return;
    }

    navigate({ to: "/questionnaire" });
  };
}
