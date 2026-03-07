# OCSS Genetic Testing Lobby Check-In Kiosk
## Advanced Logic and Communication Prompt Pack

Prepared for: Cuyahoga County Office of Child Support Services (OCSS)

Use: Copy and paste one prompt at a time into GitHub Copilot Chat.

---

## How To Use This Guide
- This guide is for the next development phase where the kiosk shell already exists and needs stronger logic, better user interaction, staff workflow improvements, and notification capability.
- Start with the `Master Refactor Prompt`.
- Then run prompts section-by-section in modular order.
- Review generated code after each prompt before moving to the next.

### Recommended Build Order
1. Advanced identifier matching and duplicate prevention
2. Confirmation screens and kiosk reset behavior
3. Appointment lifecycle and no-show logic
4. Queue prioritization, late-arrival handling, and staff quick actions
5. SMS and email confirmation services with safeguards

---

## Master Refactor Prompt

```text
Refactor my existing Streamlit OCSS genetic testing kiosk application into a more advanced operational workflow system.

Context:
- The application is for the Cuyahoga County Office of Child Support Services.
- It supports lobby check-in for genetic testing appointments imported from Hyland OnBase exports.
- The app already has a basic shell built.
- It must support linked appointment lookup by SETS case number, P-number, and participant name.
- It must improve user interaction, ease of use, and staff efficiency.

Required upgrades:
1. advanced identifier matching logic,
2. duplicate prevention,
3. confirmation screens,
4. kiosk auto-reset,
5. status lifecycle management,
6. queue prioritization,
7. late-arrival and no-show logic,
8. audit logging,
9. SMS and email confirmation logic after check-in,
10. reusable service-layer architecture.

Please review the code structure, identify missing logic, and generate improved modular code.
```

Use this prompt at the beginning of a development session.

---

## Advanced User Interaction Logic

### Guided Search and Input Classification

```text
Refactor the kiosk search logic to support guided appointment resolution.

Requirements:
- detect whether the search input is likely a SETS case number, P-number, or participant name,
- run the appropriate lookup automatically,
- show a user-friendly confirmation list if multiple matches are found,
- restrict results to active same-day appointments by default,
- display a clear assistance message if no match is found,
- avoid exposing unnecessary case details on the public kiosk screen.

Use Python and Streamlit and separate the input classification logic from the database query logic.
```

### Client Confirmation Step

```text
Add a confirmation step to the public Streamlit kiosk workflow.

After a match is found, display a confirmation card with:
- participant name
- appointment date/time
- location
- test type

Do not finalize check-in until the user clicks a confirmation button.

Add a Start Over option and ensure the screen resets cleanly after either action.
```

### Duplicate Check-In Prevention

```text
Add duplicate prevention logic to the check-in workflow.

Rules:
- if appointment status is Checked In, do not create another check-in event,
- if appointment status is Completed, block check-in,
- if appointment status is No Show, require staff override,
- prevent double submission from repeated button clicks,
- show user-friendly messages explaining the status.

Use Streamlit session state and database status validation.
```

### Public Kiosk Auto-Reset

```text
Add kiosk reset logic to the Streamlit application.

Requirements:
- after successful check-in, show a brief confirmation message,
- automatically reset the kiosk screen after a short countdown,
- clear all session state values containing appointment data,
- also support manual Start Over at any time,
- design for public-use privacy and simplicity.
```

### Public-Facing Message Improvements

```text
Improve all public-facing user messages in the Streamlit kiosk to make them clear, calm, professional, and easy to understand.

Use plain language suitable for a public office setting and avoid technical wording.
```

### Accessibility and Ease of Use

```text
Improve the accessibility and ease of use of the public Streamlit kiosk interface.

Requirements:
- large touch-friendly buttons,
- large readable text,
- simple flow with minimal steps,
- high-clarity labels,
- suitable for public lobby use.
```

---

## Advanced Business Workflow Logic

### Appointment Lifecycle Rules

```text
Create advanced appointment lifecycle logic for the OCSS genetic testing application.

Statuses:
- Scheduled
- Checked In
- In Progress
- Completed
- No Show
- Cancelled

Rules:
- enforce valid transitions only,
- prevent invalid status changes,
- require override logic for exceptional cases,
- log every transition in an audit table,
- allow staff comments on no-show and override actions.

Write reusable Python helper functions.
```

### Configurable No-Show Logic

```text
Create configurable no-show logic for the OCSS GT kiosk application.

Requirements:
- appointments start as Scheduled,
- a configurable grace period is applied after appointment time,
- after the grace period, the appointment may be flagged as Potential No Show,
- only staff may finalize No Show status,
- all no-show decisions must be logged,
- support future reporting on no-show patterns by date, location, and test type.
```

### Late Arrival Logic

```text
Add late-arrival logic to the kiosk and staff dashboard.

Requirements:
- if a client checks in after appointment time but within the grace period, status remains Checked In,
- if the client checks in after the grace period, mark the record as Late Check-In,
- display late-arrival flags on the staff queue,
- log the exact arrival time and lateness in minutes.
```

### Queue Prioritization

```text
Add queue prioritization logic to the staff dashboard.

Priority order:
1. clients checked in and waiting the longest,
2. clients checked in after scheduled time,
3. scheduled clients whose appointment time is near,
4. potential no-show appointments.

Calculate wait time, queue order, and visual urgency indicators.

Implement this in a reusable service layer and display it in the Streamlit dashboard.
```

### Audit Logging

```text
Add audit logging to the application.

Log the following events:
- appointment import
- appointment matched
- client checked in
- appointment completed
- appointment marked no-show
- record edited

Each log entry must capture:
- appointment_id
- event_type
- old_status
- new_status
- timestamp
- performed_by
- notes
```

---

## Staff Dashboard Usability Improvements

### Row-Level Quick Actions

```text
Improve the staff dashboard UX for the OCSS GT application.

Add row-level quick action buttons for:
- Mark Complete
- Mark No Show
- Add Note
- Reopen Appointment with admin/staff permission
- Re-send text or email confirmation

Use clean Streamlit patterns and prevent duplicate actions on refresh.
```

### Advanced Filters

```text
Add advanced filtering controls to the Streamlit staff dashboard.

Filters:
- date
- location
- status
- test type
- checked-in only
- no-show only
- late arrivals only

Make filters intuitive and ensure the dashboard updates efficiently.
```

### Metric Cards

```text
Add dashboard metric cards to the OCSS GT staff queue page.

Show:
- total appointments today
- checked in
- waiting
- completed
- no show
- average wait time
- late arrivals

Use clean calculations from the database and display the cards at the top of the dashboard.
```

### Structured Staff Notes

```text
Add structured staff note functionality to the OCSS GT dashboard.

Allow staff to enter quick operational notes linked to the appointment, with timestamp and staff username.

Include note categories such as:
- identity verified
- late arrival
- walk-in
- reschedule issue
- no-show reason
```

---

## Text and Email Confirmation Logic

### SMS Confirmation Service

```text
Create a Python notification service for the OCSS GT kiosk application that sends SMS confirmation messages after successful check-in.

Requirements:
- trigger only after a valid check-in is saved,
- use a provider abstraction so the app can support Twilio now and other SMS gateways later,
- validate phone number presence before sending,
- record message status, sent timestamp, and any error returned by the provider,
- prevent duplicate confirmation texts for the same check-in event,
- expose a reusable send_checkin_sms() helper function.
```

### Email Confirmation Service

```text
Create a Python email notification service for the OCSS GT kiosk application that sends check-in confirmation emails after successful check-in.

Requirements:
- send only after a successful check-in,
- use a provider abstraction so SMTP or Microsoft 365 integration can be swapped later,
- validate email address before sending,
- store sent timestamp, delivery status, and error message,
- prevent duplicate check-in emails,
- expose a reusable send_checkin_email() helper function.
```

### Unified Notification Workflow

```text
Create a unified notification workflow service for the OCSS GT kiosk application.

The service must:
- evaluate whether SMS should be sent,
- evaluate whether email should be sent,
- avoid duplicate notifications,
- log each delivery attempt,
- support preferred_contact_method values:
  - sms
  - email
  - both
  - none

Expose a function called send_checkin_notifications(appointment_id).
```

### Message Templates

```text
Create reusable message template functions for SMS and email check-in confirmations for the OCSS GT kiosk application.

The templates must:
- include appointment date, time, and location,
- remain concise and professional,
- avoid exposing unnecessary confidential information,
- support later expansion for reminders and rescheduling notices.
```

### Notification Safeguards

```text
Add notification safeguard logic to the OCSS GT application.

Requirements:
- do not send SMS if no valid mobile phone is stored,
- do not send email if no valid email address is stored,
- prevent duplicate notifications for the same check-in event,
- record provider response details,
- allow staff to manually resend a failed notification from the dashboard.
```

---

## Recommended Data Model Additions

To support advanced workflow logic and confirmations, expand the appointment record or related tables with the following fields.

| Field | Purpose |
|---|---|
| `mobile_phone` | Used for SMS check-in confirmations when available and approved. |
| `email_address` | Used for email confirmations and later reminder workflows. |
| `preferred_contact_method` | Controls whether SMS, email, both, or neither should be used. |
| `sms_opt_in` | Captures whether text messaging should be allowed. |
| `email_opt_in` | Captures whether email messaging should be allowed. |
| `last_sms_sent_at` | Prevents duplicate text confirmations and supports resend logic. |
| `last_email_sent_at` | Prevents duplicate email confirmations and supports resend logic. |
| `sms_status` / `email_status` | Stores delivery outcome such as sent, failed, skipped, or pending. |
| `notification_error` | Captures provider or validation errors for troubleshooting. |
| `late_flag` / `wait_minutes` | Supports queue prioritization, lateness tracking, and dashboard metrics. |

---

## Strong Single Prompt For Current Phase

```text
Build the matching and check-in logic for an OCSS genetic testing lobby kiosk where each appointment may be identified by SETS case number, P-number, and participant name. These identifiers must resolve to the same normalized appointment record. Prevent duplicate check-ins, support staff review when matches are ambiguous, store all status changes in an auditable SQLite database, and add SMS and email confirmation capability after a valid check-in event.
```

---

## OCSS Implementation Notes
- Keep public kiosk screens minimal and avoid displaying unnecessary PII.
- Default search results to same-day appointments unless staff broadens search.
- Require staff review when multiple similar participant names are returned.
- Do not send SMS or email confirmations unless contact data, business rules, and local approvals support it.
- Keep notification logic abstracted so county-approved providers can be swapped later.

---

## Repo-Specific Addendum (Current Build)
Use this short orientation prompt before module prompts:

```text
Use the existing OCSS GT Lobby Check-In Streamlit codebase. Preserve current local database workflows while adding modular service-layer enhancements. Respect the existing integration flag in config (`integration.mode`) so OnBase and local modes can coexist. Add unit-testable helper functions in services, keep UI logic in Streamlit pages, and avoid exposing unnecessary PII on kiosk pages.
```

---

## Additional Advanced Features: Auto-Generated COC and Related Party Pull

The next enhancement phase adds two staff-side operational features:
1. automatic chain-of-custody (COC) generation after valid check-in,
2. related-party retrieval for the same case/testing event.

### Feature 1: Auto-Generated Chain of Custody (COC) Form

The application should auto-populate a COC record after valid check-in to reduce manual entry and standardize data.

Recommended COC auto-population fields:
- sets_case_number
- p_number or administrative case number
- appointment_id
- participant_name
- participant_role
- appointment_datetime
- checkin_timestamp
- location
- test_type
- staff_user or collector_name
- specimen_tracking_number (future)
- related parties attached to same case/testing event

Recommended COC workflow:
1. client check-in is validated,
2. duplicate check-in is prevented,
3. linked appointment and parties are resolved,
4. COC record is created,
5. printable COC structure is generated,
6. staff reviews before specimen collection,
7. generated document reference is stored,
8. edits are audit logged.

### Prompt: COC Data Model and Workflow

```text
Create advanced chain-of-custody (COC) workflow logic for the OCSS GT kiosk application.

Context:
- This is for the Cuyahoga County Office of Child Support Services genetic testing workflow.
- The app already supports appointment lookup and check-in.
- After successful check-in, the system must automatically create a chain-of-custody record for staff use.

Requirements:
- generate a COC record after valid check-in,
- link the COC to the appointment_id,
- include sets_case_number, p_number, participant_name, participant_role, appointment_datetime, location, test_type, checkin_time, and staff_user,
- allow related case parties to be attached to the same COC workflow,
- maintain audit logging for any updates,
- design the solution so the form can later be rendered as PDF or printed.

Create:
1. recommended database tables,
2. Python helper functions,
3. workflow sequence,
4. validation rules,
5. notes for later PDF generation.
```

### Prompt: Auto-Populated COC Form Generation

```text
Build Python logic that auto-populates a chain-of-custody form after a successful genetic testing kiosk check-in.

Requirements:
- map appointment data into a printable COC structure,
- include linked case parties for the same case,
- allow one primary checked-in participant and additional related parties,
- support later rendering into HTML-to-PDF, DOCX-to-PDF, or direct printable layout,
- keep public kiosk logic separate from staff-only COC generation logic,
- log the time the COC was generated and by whom.

Generate modular code and recommend the best service-layer structure.
```

### Feature 2: Pull Related Parties When One Participant Checks In

The staff-side workflow should surface linked participants for the same case/testing event.

Recommended related-party logic:
- use SETS case number as primary relationship anchor,
- use P-number and appointment grouping keys as secondary anchors,
- support roles including mother, alleged father, child, guardian, and other participants,
- keep related-party visibility on staff pages only,
- allow marking each party present/absent/checked-in-separately/not-required,
- flag missing required parties when applicable,
- support one-to-many and many-to-one party relationships.

Useful additional fields:
- party_id
- party_role
- linked_case_group_id
- expected_for_test_flag
- arrival_status
- identity_verified_flag
- coc_included_flag

### Prompt: Related Party Pull Logic

```text
Create advanced related-party logic for the OCSS GT kiosk application.

Context:
- In genetic testing workflows, one checked-in participant may be connected to other case parties who belong to the same case or testing event.
- The public kiosk should remain simple, but the staff dashboard must show the full related-party context.

Requirements:
- when a participant is matched and checked in, identify all linked case parties tied to the same sets_case_number, p_number, or appointment group,
- support party roles such as mother, alleged father, child, guardian, and other related participants,
- show related parties on the staff dashboard only,
- allow staff to mark each related party as present, absent, checked in separately, or not required,
- support workflows where not all parties arrive at the same time,
- keep all updates in an audit trail.

Generate:
1. a recommended database design,
2. matching logic,
3. helper functions,
4. dashboard display logic,
5. validation rules.
```

### Prompt: Staff UX for Related Parties and COC

```text
Improve the staff dashboard UX for the OCSS GT kiosk application by adding a related-party panel and chain-of-custody controls.

Requirements:
- after a participant checks in, show a staff-side panel listing all linked case parties,
- display party role, arrival status, and whether the party is included on the chain-of-custody form,
- allow staff to confirm identity verification and attendance for each party,
- allow staff to generate or re-generate the COC form,
- prevent public kiosk users from seeing internal party relationship details,
- keep the interface easy to use during lobby and collection operations.

Write modular Streamlit code and supporting service functions.
```

### Recommended Build Priority For These Two Features
1. Build related-party data model and matching logic.
2. Add staff-side related-party display and attendance controls.
3. Create COC record-generation service.
4. Generate printable COC form template from appointment and party data.
5. Add reprint, audit, and error-handling logic.

### Strong Single Prompt For This Enhancement Phase

```text
Refactor my existing OCSS GT kiosk application to support two advanced staff-side workflow features:

1. automatic creation of a chain-of-custody (COC) form after successful client check-in, and
2. logic to pull all related case parties tied to the same genetic testing event.

Context:
- The app is for the Cuyahoga County Office of Child Support Services.
- It already has a basic Streamlit kiosk shell.
- Appointment lookup uses sets case number, p-number, and participant name.
- Staff need a workflow-friendly view of all parties connected to the case.
- The solution must be auditable and easy to use.

Please generate:
- data model updates,
- matching logic,
- related-party retrieval logic,
- chain-of-custody creation logic,
- printable form generation approach,
- staff dashboard UX recommendations,
- validation and audit controls.
```

---

End of prompt pack.
