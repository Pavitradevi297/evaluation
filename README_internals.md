# DashPoint Internals Notes

## B2c — Lifecycle bugs

Two bugs exist in the example `validate()` method. First, calling `self.save()` from `validate()` re-enters the document lifecycle and can recursively invoke validation/save hooks. Validation should calculate or validate values and return control to Frappe; it should not save the same document. Second, changing and saving Packaging Material stock during `validate()` creates a side effect every time the Delivery Order is saved, so stock can be deducted repeatedly before a delivery is actually submitted. Stock deduction belongs in the submit lifecycle (`on_submit`) and should be performed exactly once for the submitted delivery.

A corrected lifecycle shape is:

```python
def validate(self):
    self.packaging_total = sum(r.total_price or 0 for r in self.packaging_used)
    self.final_amount = (self.delivery_fee or 0) + self.packaging_total

def on_submit(self):
    for row in self.packaging_used:
        stock = frappe.db.get_value("Packaging Material", row.material, "stock_qty") or 0
        frappe.db.set_value("Packaging Material", row.material, "stock_qty", stock - row.quantity)
```

The first method is calculation-only; the stock side effect occurs once at submission.

## B2d — Optimistic locking

Frappe stores a document modification timestamp and checks it when saving. If two dispatch staff open the same Delivery Order and one saves first, the second user's in-memory document has an older modification timestamp. Frappe detects that the document changed after it was opened and raises the “Document has been modified after you have opened it” error instead of silently overwriting the first user's update. This is optimistic locking: concurrent editing is allowed, but conflicting saves are rejected.

## C3 — Rider rename and link integrity

A Rider is referenced by Link fields such as `assigned_rider`. Using `frappe.rename_doc("Rider", old_name, new_name, merge=False)` updates Link-field references maintained by Frappe. Directly changing the database name would bypass that link-integrity behavior. `merge=True` is dangerous when the target record already exists because it combines records and can move references or data into an unintended Rider. Use `merge=True` only when an intentional, reviewed merge is required.

## E — `on_update` recursion

Calling `self.save()` from `on_update()` is recursive: the save triggers another update event, which calls `save()` again, and so on. The safe pattern is to update the document once in the original lifecycle or use targeted database updates when a separate write is genuinely required. DashPoint's `on_update()` intentionally does not call `self.save()`.

## E3 — `frappe.db.get_value` vs `frappe.get_doc`

For a single scalar value such as a threshold from a Single DocType, `frappe.db.get_value("Dispatch Settings", None, "max_delivery_attempts")` is cheaper because it reads only the requested column and does not construct a Document object. `frappe.get_doc()` is appropriate when the full document, controller methods, validation, or multiple fields are needed. Use the smallest read that matches the task.

## D2 — `get_list` vs `get_all`

`frappe.get_all()` bypasses normal permission filtering and therefore is dangerous in a whitelisted method exposed to low-privilege users. It can return records a caller should never see. `frappe.get_list()` is permission-aware and is the correct choice for user-facing data retrieval. DashPoint's safe API uses `get_list()` and removes `customer_phone` and `customer_email` for non-manager callers.

## D2 — JavaScript hiding is not security

Hiding a field, button, or section in client-side JavaScript only changes the browser UI. A caller can still send an HTTP request or call a whitelisted method directly. Real security must be enforced server-side with DocType permissions, row-level `permission_query_conditions`, validation, and explicit authorization checks.

## H1 — Async `frappe.call` in `validate`

`frappe.call()` is asynchronous. A form `validate` handler expects synchronous validation to finish before the save continues, so starting an asynchronous server call there does not make the result available to the same validation cycle. Fetch asynchronous data in `setup`, `onload`, `refresh`, or a field-change handler and store the result before a synchronous validation decision is needed.

## I1 — SQL parameterization

Unsafe example:

```python
query = f"... WHERE delivery_zone = '{filters.delivery_zone}'"
```

Preferred example:

```python
query = "... WHERE delivery_zone = %(delivery_zone)s"
frappe.db.sql(query, {"delivery_zone": filters.delivery_zone})
```

Parameterized SQL separates SQL structure from user-provided values and prevents values from being interpreted as SQL syntax. DashPoint's Active Deliveries report therefore uses `%(delivery_zone)s` rather than string interpolation.

## J1 — Jinja and `before_print`

Putting a `frappe.get_all()` query directly in a Jinja print template couples database access to rendering, makes the template harder to test, and can create repeated database work inside loops. Pre-computing the required value in `before_print()` keeps database/controller logic in Python and lets the template simply reference `doc.precomputed_field`. DashPoint uses `before_print()` to set `doc.print_summary` and keeps the print template focused on presentation.

## B2b — Commit and rollback

`reassign_zone()` wraps its raw SQL update in `try/except`. It commits only after the update succeeds. On failure it rolls back, records the traceback with `frappe.log_error`, and re-raises so the caller knows the operation failed.

## E2 — Rename utility

DashPoint exposes `rename_rider(old_name, new_name)`, which calls `frappe.rename_doc("Rider", old_name, new_name, merge=False)`. Frappe updates Link-field references such as `Delivery Order.assigned_rider`; direct SQL name changes would not provide that integrity behavior.
