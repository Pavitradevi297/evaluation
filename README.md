# DashPoint

DashPoint is a pure-Frappe same-day courier dispatch system for managing delivery zones, riders, packaging stock, delivery orders, delivery attempts, receipts, permissions, reports, and printing. ERPNext is not required.

## Core implementation

Implemented Core groups through J:

- **B — ORM & Query Builder:** Query Builder stuck-delivery query and transactional rider reassignment.
- **C — Schema:** Delivery Zone, Rider, Packaging Material, Delivery Order, Packaging Usage Entry, Delivery Receipt, and Dispatch Settings.
- **D — Permissions:** three DashPoint roles, DocPerm fixtures, Rider row-level filtering, per-record sharing, and safe/unsafe API examples.
- **E — Lifecycle:** validation, submit stock checks/deduction, receipt creation, asynchronous confirmation, retry/escalation, realtime status publication, cancellation, and deletion protection.
- **F — Hooks:** idempotent installation seed, wildcard audit logging, Jinja registration, and hourly scheduler registration.
- **H — Client Scripts:** rider filtering, status indicators, delivery-attempt dialog, rider reassignment, zone warning, and packaging calculations.
- **I — Reports:** Active Deliveries Query Report and Rider Performance Script Report.
- **J — Print Format:** Jinja Delivery Receipt, Letter Head, `before_print`, currency formatting, COD banner, A4 CSS, and ten-row packaging page break.

## Installation on a fresh Frappe site

```bash
cd ~/frappe-bench
bench get-app <YOUR_REPOSITORY_URL> --branch main
bench --site <SITE_NAME> install-app dashpoint
bench --site <SITE_NAME> migrate
bench --site <SITE_NAME> clear-cache
bench restart
```

`after_install` creates North Zone, Central Zone, South Zone, the Single Dispatch Settings record, and the default DashPoint Letter Head if they do not already exist. The same master records are also included as fixtures.

## Tests

Run the complete local suite with:

```bash
bench --site <SITE_NAME> run-tests --app dashpoint
```

The test suite uses `FrappeTestCase` and factory functions. Frappe's automatic rollback makes most explicit `tearDown()` database cleanup unnecessary.

## Fixtures

After confirming a development site, export current fixtures with:

```bash
bench --site <SITE_NAME> export-fixtures --app dashpoint
```

The repository already contains fixtures for the three roles, their DocPerm records, the three Delivery Zones, Dispatch Settings, and DashPoint Letter Head.

## Reports

### Active Deliveries

A parameterized Query Report listing all non-delivered/non-cancelled orders, optionally filtered by Delivery Zone.

### Rider Performance

A permission-aware Script Report with date/rider filters, Total vs Delivered bar chart, report summary, success-rate formatter, and clickable Rider links. It uses `frappe.get_list()` so Rider row-level restrictions remain effective.

## Print format

The Delivery Receipt uses the default DashPoint Letter Head, `get_dispatch_center_name()`, `before_print()`, `format_value()`, a COD Pending banner, A4/1cm CSS, print-only CSS, and a packaging-table page break after ten rows.

## Security notes

- Server-side permissions and row-level conditions are authoritative; JavaScript hiding is not a security boundary.
- `unsafe_get_delivery_order_data()` exists only as the deliberately unsafe comparison required by the exercise. Use `safe_get_delivery_order_data()` for application behavior.
- The stock deduction in `on_submit()` is a controlled server-side side effect and uses a direct database update so it is not blocked by the submitting user's Packaging Material permissions.

## Documentation

See [`README_internals.md`](README_internals.md) for the required ORM, lifecycle, security, async, SQL, and Jinja explanations.
