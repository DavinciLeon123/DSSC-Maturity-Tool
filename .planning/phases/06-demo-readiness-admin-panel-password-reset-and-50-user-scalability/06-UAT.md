---
status: complete
phase: 06-demo-readiness-admin-panel-password-reset-and-50-user-scalability
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md, 06-04-SUMMARY.md, 06-05-SUMMARY.md, 06-06-SUMMARY.md
started: 2026-03-06T17:10:00Z
updated: 2026-03-06T17:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Autosave badge — saving/saved states
expected: While navigating between questionnaire topics, an autosave badge appears near the top of the page. It briefly shows "Saving..." (grey) while the answer is being sent, then "Saved" (green) on success. No badge visible when idle.
result: pass

### 2. Next button disabled during save
expected: When clicking Next to go to the next topic while a save is in-flight, the Next button is disabled (unclickable) until the save completes.
result: pass

### 3. Submission confirmation screen
expected: After completing all questionnaire topics and clicking Finish/Submit, a confirmation screen appears (not the dashboard). It shows something like "Your submission is complete" with a checkmark and a "Generate Report" button that leads to the dashboard.
result: pass

### 4. Session expired redirect
expected: When a JWT expires mid-session (or is manually invalidated), the next API call redirects the user to /login?session=expired. The login page shows an amber banner reading "Your session expired. Please log in again."
result: pass

### 5. Forgot password link on login page
expected: On the login page (/login), a "Forgot your password?" link is visible below the sign-in form. Clicking it navigates to /forgot-password.
result: pass

### 6. Forgot password email form
expected: At /forgot-password, there is an email input form. After entering any email address and submitting, a success message appears ("If that email is registered, we've sent a reset link.") — even for unregistered emails (no enumeration). A "Back to Sign In" link is visible.
result: pass

### 7. Reset link in backend logs (dev mode)
expected: After submitting the forgot-password form with a registered email, the backend Docker logs show a line like "[DEV] Password reset link for <email>: http://localhost:5173/reset-password?token=..."
result: pass

### 8. Reset password page
expected: Navigating to /reset-password?token=<valid_token> shows a form with two password fields (new password + confirm). Passwords must match and be at least 12 characters. On success, user is redirected to /login?reset=success.
result: pass

### 9. Login reset-success banner
expected: After a successful password reset, the login page (/login?reset=success) shows a green banner reading something like "Password updated. Please sign in."
result: pass

### 10. Admin link in sidebar — visible for ADMIN only
expected: When logged in as the admin account, an "Admin" link appears in the left sidebar navigation. When logged in as a regular user, no Admin link is visible.
result: pass

### 11. Admin panel — Users tab
expected: At /admin, the Users tab shows a table of all registered users with columns for email, role, and a delete button. Expanding a row shows participant_type, initiative name, status, answer count, and registration date. The admin account row shows "Protected" instead of a delete button.
result: pass

### 12. Admin panel — Questionnaires tab
expected: The Questionnaires tab shows a table of all initiatives with columns for owner email, initiative name, type, status, answer count, and created date. Each row has a delete button with Popconfirm.
result: pass

### 13. Admin panel — CSV export
expected: In the Actions tab, clicking "Download CSV" triggers a file download of a CSV named mami-dataset.csv. The file contains one row per questionnaire answer with columns: user_email, initiative_name, participant_type, initiative_status, question_id, mami_code, answer_value, followup_other.
result: pass

### 14. Admin panel — Reset Demo
expected: In the Actions tab, clicking the red "Reset Demo Data" button opens a confirmation modal. After confirming, all non-admin users and their data are deleted. The admin account remains intact.
result: skipped
reason: Destructive — preferred not to wipe test data

### 15. Non-admin redirect from /admin
expected: When logged in as a regular (non-admin) user and navigating directly to /admin, the user is automatically redirected to /dashboard (not shown an error page).
result: pass

## Summary

total: 15
passed: 14
issues: 0
pending: 0
skipped: 1

## Gaps

[none yet]
