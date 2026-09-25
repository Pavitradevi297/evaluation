DashPoint Internals Notes

B2c — Lifecycle bugs

There are two bugs in the example validate() method. First, calling self.save() from validate() re-enters the document lifecycle and can cause recursive validation or save hooks. Calculating or validating values is fine for validate(), but saving the same document again is not. Second, modifying and saving Packaging Material stock from validate() causes a side effect every time the Delivery Order is saved. Stock should only be deducted once per delivery, at the moment of submission. A corrected lifecycle looks like:


def validate(self):
self.packaging_total = sum(r.total_price or 0 for r in self.packaging_used)
self.final_amount = (self.delivery_fee or 0) + self.packaging_total
def on_submit(self):
for row in self.packaging_used:
stock = frappe.db.get_value("Packaging Material", row.material, "stock_qty") or 0
frappe.db.set_value("Packaging Material", row.material, "stock_qty", stock - row.quantity)
The first method only calculates values, and the stock side effect only occurs once, at submission.


B2d — Optimistic locking

Frappe stores a timestamp for the document modification time and checks it when saving. If two dispatchers are working on the same Delivery Order and one saves their changes first, then in the background, the modification timestamp for the second dispatcher's in-memory copy of the Delivery Order will be older than the newer timestamp on disk. When the second dispatcher tries to save, Frappe will notice the timestamp mismatch and raise an error Document has been modified after you have opened it instead of silently overwriting the first dispatcher's changes. This is optimistic locking — concurrency is allowed, but the framework defends against accidental data loss due to parallel edits.



C3 — Rider rename and link integrity

A Rider is referenced by Link fields such as assigned_rider. Using frappe.rename_doc("Rider", old_name, new_name, merge=False) will update all Link-type references to new_name maintained by Frappe. If we were to directly modify the database name for a Rider, it would bypass the link-integrity system. With merge=True , we could accidentally merge two Riders if the target record already exists. Only use merge=True if we explicitly want to merge documents.



E — on_update recursion

Calling self.save() from on_update() is recursive. The save() will call update(), which calls save(), etc. The safe pattern is to make changes to the document once, either in the original lifecycle or with a direct database update if a separate write is deliberately needed. DashPoint's on_update() deliberately does not call self.save().



E3 — db.get_value vs get_doc

For a scalar value such as a threshold in a Single DocType, frappe.db.get_value("Dispatch Settings", None, "max_delivery_attempts") is cheaper than frappe.get_doc(). It avoids instantiating a Document object when only a few scalar fields are needed. Use frappe.get_doc() for queries that need the entire document, its controller methods, and validations. Always use the narrowest possible query to fetch only what is needed.



D2 — get_list vs get_all

frappe.get_all() bypasses all permission filters and should not be used in whitelisted methods for unprivileged users. A method decorated with @frappe.whitelist() and called from the browser can return records the current user should not see. Use frappe.get_list() for user-facing queries. DashPoint's safe API uses get_list() and strips customer_phone and customer_email for non-manager users.



D2 — JavaScript hiding is not security

Hiding a field, button, or section in a client-side JavaScript is ineffective as a security measure. The user can directly call an API or use browser developer tools to modify data. Security checks should always be implemented server-side. In the Desk UI, permission are enforced with DocType permissions, row-level permission_query_conditions, and server-side validations. For the public API, use permission-aware frappe.get_list() and similar calls to enforce security.



H1 — Async frappe.call in validate()

frappe.call() is asynchronous. A form's validate() handler should not make async server calls, because the framework will not wait for the promise to resolve before proceeding to the next step. Async data should be fetched in setup, onload, refresh, or a field-change handler. Store the result in a variable and use it later when a synchronous validation is needed.



I1 — SQL parameterization

Unsafe example:
query = f"... WHERE delivery_zone = '{filters.delivery_zone}'"
Preferred example:
query = "... WHERE delivery_zone = %(delivery_zone)s"
frappe.db.sql(query, {"delivery_zone": filters.delivery_zone})
Always use parameterized queries to prevent SQL injection. The parameter name in the query string must match the key in the second argument to db.sql(). The Active Deliveries report in DashPoint uses %(delivery_zone)s instead of string interpolation.



J1 — Jinja and before_print

It is not safe to put a frappe.get_all() query directly in a Jinja print template. It bloats the template with database logic and requires running the query inside a loop. A better practice is to precompute the necessary value in a controller's before_print() hook and then access it as doc.precomputed_field in the template. DashPoint's print templates use doc.print_summary set in before_print() .



B2b — Commit and rollback

reassign_zone() wraps the raw SQL update in a try/except block. It commits only if the raw SQL was successfully updated. It logs an error and re-raises the exception so that the caller knows that the database operation failed.



E2 — Rename utility

DashPoint exposes rename_rider(old_name, new_name) , which calls frappe.rename_doc("Rider", old_name, new_name, merge=False) . Frappe provides built-in support for renaming and updating Link fields. Direct database manipulation would not trigger the link-integrity system.



K2 — N+1 Query Detection and Fix

The N+1 problem appears when Delivery Orders are fetched in one query, but a separate query is made for each Rider.



Problematic approach

orders = frappe.get_all(
"Delivery Order",
fields=["name", "assigned_rider"]

)



for o in orders:
rider = frappe.get_doc("Rider", o.assigned_rider)
print(rider.rider_name, rider.phone)
L1 — Custom Whitelisted Method


The Delivery Order controller in DashPoint exposes get_stuck_deliveries() as a custom whitelisted method:


@frappe.whitelist()
def get_stuck_deliveries():
...
L2 — Outgoing Webhook / Async Delivery Confirmation
When a Delivery Order is submitted, on_submit() queues the delivery confirmation with frappe.enqueue() :
frappe.enqueue(
"dashpoint.dashpoint.api.send_delivery_confirmation",
queue="short",

delivery_order_name=self.name,
)

N1 — ignore_permissions Audit

In general, ignore_permissions=True should only be used for server-side operations where the application itself must perform an internal process.



Installation defaults



install.py uses ignore_permissions=True when creating default Delivery Zones, Dispatch Settings and the default Letter Head. These records should not be created by a Desk user, so it is normal to bypass permissions here.


Scheduler Audit Log


tasks.py uses ignore_permissions=True when creating the stuck_reattempt_check sentinel Audit Log record. The scheduler should not depend on the permissions of the user it is running as.


Delivery Receipt creation


Delivery Order.on_submit() creates a system-provided Delivery Receipt with ignore_permissions=True . The Receipt is a side effect of submitting a completed Delivery Order and should not be gated by the user's explicit Delivery Receipt creation permissions.


Delivery attempt update


The server-side record_delivery_attempt() method uses save(ignore_permissions=True) because the controlled backend process should update the Delivery Order as part of the delivery lifecycle. This is not a user-facing change, and client-side field hiding should not be used as the sole security measure.


Receipt cancellation


When a Delivery Order is cancelled, its system-provided submitted Delivery Receipt is cancelled internally with permissions bypassed so that the linked document can remain consistent with the parent lifecycle.



These permission bypasses are limited to trusted server-side code such as installation, scheduler jobs, document lifecycle events, and are not used as a general-purpose replacement for the role-based permissions system.



N1 — JavaScript Hiding Is Not Security



The use of JavaScript to hide fields in Desk is appropriate as a user-interface customization, but should not be used as a security measure. A user can access or modify the field directly through the API, or via the browser's developer tools.



Actual protection is enforced through:
DocType role permissions
permission_query_conditions for row-level access control for Delivery Order
server-side DocType validations
explicit server-side permission checks in whitelisted methods



Using permission-aware get_list() for queries in the public API
For example, the safe Delivery Order API uses get_list() and not get_all() so that Frappe's permission system can participate in the query.

Thus, JavaScript field hiding should not be used as a security measure.
L2 — Outgoing Webhook on Submit

DashPoint sends an outgoing webhook after successfully submitting a Delivery Order.
The webhook URL is defined in the Webhook URL field in the Dispatch Settings Single DocType.


Delivery Order.on_submit() uses frappe.enqueue() to call dashpoint.dashpoint.api.send_webhook in the background:
frappe.enqueue(
__PROTECTED_FOREIGN_QUOTE_3__,
queue="short",
delivery_order_name=self.name,
)

The background job:
reads the webhook URL from the Dispatch Settings
loads the Delivery Order document
constructs a JSON payload with event type, Delivery Order name, and final amount
uses a 5s timeout for the HTTP request
calls raise_for_status() for any HTTP error response
logs errors to Frappe's logger
logs successful webhook delivery to Frappe's dashpoint logger



If the webhook URL is not defined, the background job does not attempt to make an HTTP request.
