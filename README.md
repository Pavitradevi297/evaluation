DashPoint

DashPoint is a pure-Frappe same-day courier dispatch system for managing delivery zones, riders, packaging stock, delivery orders, delivery attempts, receipts, permissions, reports, and printing. ERPNext is not required.


Core implementation


B — ORM & Query Builder: query builder used for stuck-delivery query and transactional rider reassignment

C — Schema: Delivery Zone, Rider, Packaging Material, Delivery Order, Packaging Usage Entry, Delivery Receipt, and Dispatch Settings

D — Permissions: three DashPoint roles, DocPerm fixtures, rider row-level filter, per-record sharing, and safe/unsafe API examples

E — Lifecycle: validation, submit stock checks/deduction, receipt creation, async confirmation, retry/escalation, realtime status publication, cancellation, and deletion protection

F — Hooks: idempotent installation seed, wildcard audit logging, Jinja registration, and hourly scheduler registration

H — Client Scripts: rider filtering/status indicators/delivery-attempt dialog/rider reassignment/zone warning/packaging calculations

I — Reports: Active Deliveries Query Report and Rider Performance Script Report

J — Print Format: Jinja Delivery Receipt, Letter Head, before_print, currency formatting, COD banner, A4 CSS, and ten-row packaging page break

Installation on a fresh Frappe site

cd ~/frappe-bench

bench get-app --branch main

bench --site install-app dashpoint

bench --site migrate

bench --site clear-cache

bench restart

after_install creates North Zone, Central Zone, South Zone, the Single Dispatch Settings record, and the default DashPoint Letter Head if they do not already exist. The same master records are also included as fixtures.



Tests

The entire local test suite can be run with:

bench --site run-tests --app dashpoint

The test suite uses FrappeTestCase and factory functions. Due to Frappe’s auto-rollback, most tests do not require an explicit tearDown() that would delete test records from the database.



Fixtures

Once you have a development site up and running, you can export your current fixtures with:


bench --site export-fixtures --app dashpoint

The repo already includes fixtures for the three roles, their DocPerm entries, the three Delivery Zones, Dispatch Settings, and the DashPoint Letter Head.

Reports

Active Deliveries

A parameterized Query Report that lists all non-delivered/non-cancelled Delivery Orders, optionally filtered by Delivery Zone.


Rider Performance

A permission aware Script Report with date/rider filters, Total vs Delivered bar chart, report summary, success-rate formatter, and clickable Rider links. Uses frappe.get_list() to ensure that row-level restrictions for Riders are still respected.


Print format

The Delivery Receipt DocType is printed with the default DashPoint Letter Head, get_dispatch_center_name(), before_print(), format_value() hooks, COD Pending banner, A4/Landscape CSS, print CSS (for hiding), and a ten-row packaging-table page-break.


Security notes

Server-side permissions and row-level restrictions take precedence over any client-visible hiding of elements.

unsafe_get_delivery_order_data() only exists to provide the explicitly unsafe example requested in the assignment. You should always use safe_get_delivery_order_data() for app behaviors.

The stock deduction on delivery receipt submit is a controlled server-side effect and should not be visible to or by the end-user requesting the receipt. As such, it uses a direct database update and is not wrapped inside any permission checks.

Documentation

See README_internals.md for the ORM requirements, lifecycles, security, async tasks, SQL, and Jinja conventions used in this implementation.
