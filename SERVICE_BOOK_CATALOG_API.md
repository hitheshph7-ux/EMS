# Service Book Catalog API

Catalog endpoints are available under `/api/`. List and retrieve operations are
readable without authentication. Creating and updating catalog records requires
an authenticated Django staff user. Catalog records cannot be deleted through
the API so that future service-history references remain stable.

## Designations

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/designations/` | List designations |
| POST | `/api/designations/` | Create a designation (staff only) |
| GET | `/api/designations/{id}/` | Retrieve a designation |
| PUT, PATCH | `/api/designations/{id}/` | Update a designation (staff only) |

Fields: `id` (read-only), `code` (unique), `name`, `description`, and
`is_active`.

## Pay scales

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/pay-scales/` | List pay scales |
| POST | `/api/pay-scales/` | Create a pay scale (staff only) |
| GET | `/api/pay-scales/{id}/` | Retrieve a pay scale |
| PUT, PATCH | `/api/pay-scales/{id}/` | Update a pay scale (staff only) |

Fields: `id` (read-only), `code` (unique), `min_pay`, `max_pay`,
`increment_steps`, `revision_order`, `effective_date`, and `is_active`.
`increment_steps` retains the model's existing JSON format: a list of numeric
increment amounts, for example `[500, 750]`. Minimum pay must not exceed maximum
pay.

Invalid or duplicate catalog data returns HTTP 400 with field-specific
validation errors. Unauthorized write requests return HTTP 403. Unsupported
methods, including DELETE, return HTTP 405.

## Employee service-book profiles

This checkout has no shared Employee model. The Module 3 profile stores the
employee's identifying details against the stable employee CEN; it does not
create or seed sample employees. Profile reads and writes require an
authenticated staff user.

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/employee-profiles/` | List or create an employee profile |
| GET, PUT, PATCH | `/api/employee-profiles/{id}/` | Read or update profile details |

Fields: `id`, `employee_cen` (unique), `full_name`, `date_of_birth`, `email`,
`phone`, `department`, `created_at`, and `updated_at`. The list endpoint
supports `?employee_cen={cen}`.

## Service events and employee state

Module 3's event and employee-record endpoints require an authenticated staff
user. Records are filtered by `employee_cen` when that query parameter is
provided. Service events cannot be deleted. Draft events can be edited; approved
event details and their captured designation/pay-scale labels are immutable.

| Method | Endpoint | Purpose |
|---|---|---|
| GET, POST | `/api/service-events/` | List or create a draft event |
| GET, PUT, PATCH | `/api/service-events/{id}/` | Read or edit an unlocked draft |
| POST | `/api/service-events/{id}/submit/` | Validate and submit a draft |
| POST | `/api/service-events/{id}/approve/` | Approve a submitted event |
| POST | `/api/service-events/{id}/cancel/` | Cancel an event; JSON body requires `reason` |
| POST | `/api/service-events/{id}/lock/` | Lock an approved event |
| POST | `/api/service-events/{id}/unlock/` | Unlock an approved event |
| GET | `/api/service-events/{id}/signature/` | Read the approval signature |
| GET | `/api/service-snapshots/` | Read rebuilt employee snapshots |
| GET | `/api/service-state/?employee_cen={cen}&date=YYYY-MM-DD` | Reconstruct employee state from approved event history |
| GET, POST | `/api/probation-records/` | Read or create probation records |
| GET | `/api/transfers/` | Read transfer workflows |
| POST | `/api/transfers/{id}/relieve/` | Record relieving-society acceptance |
| POST | `/api/transfers/{id}/accept/` | Record receiving-society acceptance |
| GET, POST | `/api/recruitment-records/` | Read or create recruitment records |
| GET, POST | `/api/scanned-service-books/` | Read or upload scanned documents |
| GET | `/api/scanned-service-books/{id}/download/` | Download a scan (staff-only) |
| GET, POST | `/api/acr-records/` | Read or create ACR records |
| POST | `/api/acr-records/{id}/lock/` or `/unlock/` | Lock or unlock an ACR |
| GET | `/api/audit-history/?employee_cen={cen}` | Read audit history |

Event payloads are JSON objects and are validated by event type:

* `APPOINTMENT`: `designation_id`, `pay_scale_id`, `pay_amount`, `society_cen`.
* `PROMOTION` / `DESIGNATION_CHANGE`: `designation_id`; optional `pay_scale_id`
  and `pay_amount`. Promotion must increase the designation's `level`.
* `INCREMENT`: `pay_scale_id`, `increment_amount`, and `new_pay`. The amount
  must be an allowed scale step and new pay must equal previous pay plus it.
* `PAY_REVISION`: `pay_scale_id` and `pay_amount`.
* `TRANSFER`: `to_society_cen`. The relieving and receiving acceptance actions
  must both complete before approval.
* `PROBATION_EXTENDED`: `new_end_date` and `reason`.
* `LEAVE`: `start_date` and `end_date`; the event date must match its start.
* `SUSPENSION`, `REINSTATEMENT`, and `TERMINATION`: `reason`.
* `PROBATION_CONFIRMED`: an empty object is permitted; approval requires an
  active probation record.

Approval captures designation and pay-scale codes/names in event history,
creates a dummy SHA-256 signature, records audit history, and rebuilds the
snapshot from approved, non-cancelled events. Historical state queries replay
the approved event history and do not read the latest snapshot. Cancelling an
approved event records the cancellation; it does not delete the event, and
historical queries before its cancellation date continue to include it.

## Shared Employee and Society model integration

This checkout does not contain the teammates' Employee or Society models. To
avoid creating duplicate models or guessing foreign-key targets, this Module 3
implementation currently stores the employee's CEN and society CEN as stable
identifier values. Employee contact details are kept in the Module 3
`EmployeeServiceProfile` until the shared Employee model is available.
`ServiceBookService.rebuild(employee)` reads the Employee
CEN attribute configured by `SERVICE_BOOK_EMPLOYEE_CEN_FIELD` (default
`cen`; it also recognizes `CEN` and `employee_cen`). A real foreign-key and
society-membership permission integration must be wired once those shared
model labels and relationship fields are available.

## Service Book interface

The landing page is a functional staff workspace for profiles, current and
historical service state, event timelines and approval actions, probation,
recruitment, scanned documents, ACRs, and audit history. All displayed records
are loaded from the API; no demo employee records are seeded. Sign in through
Django admin (`/admin/login/?next=/`) to use the staff-only APIs.

## Database configuration

SQLite remains the local default so existing development data and tests remain
usable. PostgreSQL is supported by setting `DB_ENGINE=postgresql` and providing
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in the process
environment before running migrations and the server. The PostgreSQL driver is
included in `requirements.txt`.
