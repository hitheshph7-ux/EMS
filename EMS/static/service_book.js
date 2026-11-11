(() => {
    "use strict";

    const apiRoot = "/api/";
    const staffEnabled = document.body.dataset.staff === "true";
    const elements = (selector, root = document) => [...root.querySelectorAll(selector)];
    const element = (id) => document.getElementById(id);
    const picker = element("employee-picker");
    const eventTypes = {
        APPOINTMENT: "Appointment",
        PROMOTION: "Promotion",
        DESIGNATION_CHANGE: "Designation change",
        INCREMENT: "Salary increment",
        PAY_REVISION: "Pay revision",
        TRANSFER: "Transfer",
        PROBATION_CONFIRMED: "Probation confirmation",
        PROBATION_EXTENDED: "Probation extension",
        LEAVE: "Leave",
        SUSPENSION: "Suspension",
        REINSTATEMENT: "Reinstatement",
        TERMINATION: "Termination",
    };
    const store = {
        profiles: [],
        designations: [],
        payScales: [],
        employeeCen: "",
        profile: null,
        events: [],
        workflows: [],
        probations: [],
        recruitments: [],
        documents: [],
        acrRecords: [],
        audits: [],
        state: null,
    };

    function showNotice(message, kind = "success") {
        const notice = element("notice");
        notice.textContent = message;
        notice.className = `notice${kind === "error" ? " error" : kind === "info" ? " info" : ""}`;
        notice.hidden = false;
        window.clearTimeout(showNotice.timer);
        showNotice.timer = window.setTimeout(() => { notice.hidden = true; }, 6500);
    }

    function csrfToken() {
        const token = document.cookie.split("; ").find((cookie) => cookie.startsWith("csrftoken="));
        return token ? decodeURIComponent(token.slice("csrftoken=".length)) : "";
    }

    function errorMessage(data, fallback) {
        if (typeof data === "string") return data;
        if (data && typeof data === "object") {
            const messages = Object.entries(data).flatMap(([key, value]) => {
                const text = Array.isArray(value) ? value.join(", ") : typeof value === "object"
                    ? errorMessage(value, "") : String(value);
                return text ? [`${key === "detail" ? "" : `${key}: `}${text}`] : [];
            });
            if (messages.length) return messages.join(" · ");
        }
        return fallback;
    }

    async function request(path, options = {}) {
        const headers = new Headers(options.headers || {});
        if (options.body && !(options.body instanceof FormData)) {
            headers.set("Content-Type", "application/json");
        }
        if (!["GET", "HEAD"].includes((options.method || "GET").toUpperCase())) {
            headers.set("X-CSRFToken", csrfToken());
        }
        const response = await fetch(`${apiRoot}${path}`, {
            ...options,
            headers,
            credentials: "same-origin",
        });
        const contentType = response.headers.get("content-type") || "";
        const data = contentType.includes("application/json") ? await response.json() : null;
        if (!response.ok) {
            throw new Error(errorMessage(data, `Request failed (${response.status}).`));
        }
        return data;
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>"']/g, (character) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
        })[character]);
    }

    function dateValue(value) {
        if (!value) return "—";
        const parsed = new Date(`${value}T00:00:00`);
        return Number.isNaN(parsed.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
            year: "numeric", month: "short", day: "numeric",
        }).format(parsed);
    }

    function money(value) {
        if (value === null || value === undefined || value === "") return "—";
        const amount = Number(value);
        return Number.isFinite(amount) ? new Intl.NumberFormat(undefined, {
            style: "currency", currency: "INR", maximumFractionDigits: 2,
        }).format(amount) : String(value);
    }

    function statusClass(status) {
        const normalized = String(status || "").toLowerCase();
        if (normalized === "active" || normalized === "approved" || normalized === "confirmed") return `status-${normalized}`;
        if (normalized === "suspended" || normalized === "terminated" || normalized === "cancelled") return `status-${normalized}`;
        if (normalized === "probation" || normalized === "draft" || normalized === "submitted" || normalized === "extended") {
            return `status-${normalized === "extended" ? "probation" : normalized}`;
        }
        return "status-neutral";
    }

    function statusPill(status) {
        return `<span class="status-pill ${statusClass(status)}">${escapeHtml(String(status || "Unknown").replaceAll("_", " "))}</span>`;
    }

    function employeeQuery(path) {
        return `${path}?employee_cen=${encodeURIComponent(store.employeeCen)}`;
    }

    function setEmployeeFormState() {
        const enabled = Boolean(store.employeeCen);
        elements("#recruitment-form button, #probation-form button, #document-form button, #acr-form button, #event-form button").forEach((button) => {
            button.disabled = !enabled;
        });
    }

    function renderProfilePicker() {
        const selected = store.employeeCen;
        picker.innerHTML = `<option value="">Select an employee</option>${store.profiles.map((profile) =>
            `<option value="${escapeHtml(profile.employee_cen)}">${escapeHtml(profile.full_name)} · ${escapeHtml(profile.employee_cen)}</option>`
        ).join("")}`;
        picker.value = selected;
    }

    function renderProfile() {
        const profile = store.profile;
        const state = store.state;
        const name = profile?.full_name || store.employeeCen;
        element("employee-name").textContent = name || "No employee selected";
        element("employee-meta").textContent = profile
            ? [profile.employee_cen, profile.date_of_birth ? `Born ${dateValue(profile.date_of_birth)}` : "", profile.department, profile.email, profile.phone].filter(Boolean).join(" · ")
            : store.employeeCen ? `CEN ${store.employeeCen} · Employee profile details have not been added.` : "Choose an employee record or add a new one to get started.";
        element("employee-avatar").textContent = profile?.full_name
            ? profile.full_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()
            : store.employeeCen ? store.employeeCen.slice(0, 2).toUpperCase() : "—";
        element("edit-profile").disabled = !profile;
        const currentStatus = state?.employment_status || "No service data";
        const badge = element("employment-status");
        badge.textContent = String(currentStatus).replaceAll("_", " ");
        badge.className = `status-pill ${statusClass(currentStatus)}`;
        element("record-date").textContent = state?.as_of_date ? `Updated ${dateValue(state.as_of_date)}` : "";
        element("current-designation").textContent = state?.designation_name
            ? `${state.designation_name}${state.designation_code ? ` (${state.designation_code})` : ""}`
            : "No approved appointment";
        element("current-designation-level").textContent = state?.designation_level ?? "—";
        element("current-designation-description").textContent = state?.designation_description || "—";
        element("current-scale").textContent = state?.pay_scale_code || "—";
        element("current-pay-range").textContent = state?.pay_scale_min_pay != null && state?.pay_scale_max_pay != null
            ? `${money(state.pay_scale_min_pay)}–${money(state.pay_scale_max_pay)}` : "—";
        element("current-pay").textContent = money(state?.current_pay);
        element("current-scale-revision").textContent = state?.pay_scale_revision_order != null
            ? `${state.pay_scale_revision_order} · ${dateValue(state.pay_scale_effective_date)}` : "—";
        element("current-scale-steps").textContent = state?.pay_scale_increment_steps?.length
            ? state.pay_scale_increment_steps.map(money).join(", ") : "—";
        element("current-society").textContent = state?.society_cen || "—";
        element("current-probation").textContent = state?.probation_status || "—";
        element("current-status").textContent = String(state?.employment_status || "—").replaceAll("_", " ");
    }

    function eventSummary(event) {
        const payload = event.payload || {};
        const designation = store.designations.find((item) => String(item.id) === String(payload.designation_id));
        const scale = store.payScales.find((item) => String(item.id) === String(payload.pay_scale_id));
        if (event.event_type === "APPOINTMENT") {
            return [
                payload.designation_name_snapshot || designation?.name,
                payload.pay_scale_code_snapshot || scale?.code,
                payload.pay_amount ? money(payload.pay_amount) : "",
                payload.society_cen ? `Society ${payload.society_cen}` : "",
            ].filter(Boolean).join(" · ");
        }
        if (event.event_type === "PROMOTION" || event.event_type === "DESIGNATION_CHANGE") {
            return [payload.designation_name_snapshot || designation?.name, payload.pay_scale_code_snapshot || scale?.code,
                payload.pay_amount ? money(payload.pay_amount) : ""].filter(Boolean).join(" · ");
        }
        if (event.event_type === "INCREMENT") return `${money(payload.increment_amount)} increment · New pay ${money(payload.new_pay)}`;
        if (event.event_type === "PAY_REVISION") return `${payload.pay_scale_code_snapshot || scale?.code || "Pay scale"} · ${money(payload.pay_amount)}`;
        if (event.event_type === "TRANSFER") return `Receiving society ${payload.to_society_cen || "—"}`;
        if (event.event_type === "PROBATION_EXTENDED") return `Until ${dateValue(payload.new_end_date)} · ${payload.reason || ""}`;
        if (event.event_type === "LEAVE") return `${dateValue(payload.start_date)} – ${dateValue(payload.end_date)}`;
        return payload.reason || "";
    }

    function actionButton(label, action, id, style = "secondary", extra = "") {
        return `<button type="button" class="button button-${style}" data-action="${escapeHtml(action)}" data-id="${escapeHtml(id)}" ${extra}>${escapeHtml(label)}</button>`;
    }

    function eventActions(event) {
        const actions = [];
        if (event.status === "DRAFT" && !event.is_locked) actions.push(actionButton("Submit", "submit", event.id, "primary"));
        if (event.status === "SUBMITTED" && !event.is_locked) {
            if (event.event_type === "TRANSFER") {
                const workflow = store.workflows.find((item) => item.event === event.id);
                if (workflow?.status === "PENDING_RELIEF") actions.push(actionButton("Record relief", "relieve", workflow.id));
                if (workflow?.status === "RELIEVED") actions.push(actionButton("Accept transfer", "accept", workflow.id));
                if (workflow?.status === "ACCEPTED") actions.push(actionButton("Approve", "approve", event.id, "primary"));
            } else {
                actions.push(actionButton("Approve", "approve", event.id, "primary"));
            }
        }
        if (event.status === "APPROVED") {
            actions.push(actionButton(event.is_locked ? "Unlock" : "Lock", event.is_locked ? "unlock" : "lock", event.id));
        }
        if (["DRAFT", "SUBMITTED", "APPROVED"].includes(event.status) && !event.is_locked) {
            actions.push(actionButton("Cancel", "cancel", event.id, "danger"));
        }
        return actions.join("");
    }

    function renderEvents() {
        const timeline = element("event-timeline");
        const events = [...store.events].sort((a, b) => b.effective_date.localeCompare(a.effective_date) || b.id - a.id);
        element("stat-events").textContent = events.length;
        element("stat-pending").textContent = events.filter((event) => ["DRAFT", "SUBMITTED"].includes(event.status)).length;
        if (!events.length) {
            timeline.className = "timeline empty-state";
            timeline.textContent = "No service events have been recorded for this employee.";
            element("approval-list").className = "approval-list empty-state";
            element("approval-list").textContent = "There are no drafts or pending approvals.";
            return;
        }
        timeline.className = "timeline";
        timeline.innerHTML = events.map((event) => {
            const summary = eventSummary(event);
            const workflow = store.workflows.find((item) => item.event === event.id);
            return `<article class="timeline-item"><span class="timeline-dot"></span>
                <div class="timeline-head"><strong>${escapeHtml(eventTypes[event.event_type] || event.event_type)}</strong>${statusPill(event.status)}
                <span class="timeline-date">${escapeHtml(dateValue(event.effective_date))}</span></div>
                ${summary ? `<p class="timeline-copy">${escapeHtml(summary)}</p>` : ""}
                ${workflow ? `<p class="timeline-copy">Transfer workflow: ${escapeHtml(workflow.status.replaceAll("_", " ").toLowerCase())}</p>` : ""}
                <div class="timeline-actions">${eventActions(event)}</div></article>`;
        }).join("");
        const approvalEvents = events.filter((event) => ["DRAFT", "SUBMITTED"].includes(event.status));
        const approvals = element("approval-list");
        if (!approvalEvents.length) {
            approvals.className = "approval-list empty-state";
            approvals.textContent = "There are no drafts or pending approvals.";
        } else {
            approvals.className = "approval-list";
            approvals.innerHTML = approvalEvents.map((event) => `
                <div class="approval-row"><div class="approval-main"><strong>${escapeHtml(eventTypes[event.event_type] || event.event_type)}</strong>
                <span>${escapeHtml(dateValue(event.effective_date))}${eventSummary(event) ? ` · ${escapeHtml(eventSummary(event))}` : ""}</span></div>
                ${statusPill(event.status)}</div>`).join("");
        }
    }

    function renderRecordList(id, records, emptyMessage, renderItem) {
        const target = element(id);
        if (!records.length) {
            target.className = "record-list empty-state";
            target.textContent = emptyMessage;
            return;
        }
        target.className = "record-list";
        target.innerHTML = records.map(renderItem).join("");
    }

    function renderRecords() {
        renderRecordList("recruitment-list", store.recruitments, "No recruitment or joining records for this employee.", (record) => `
            <div class="record-row"><div><strong>${escapeHtml(record.recruitment_mode)} · ${escapeHtml(dateValue(record.recruitment_date))}</strong>
            <span>${escapeHtml(record.reference_number || "No reference number")}${record.details && Object.keys(record.details).length ? ` · ${escapeHtml(JSON.stringify(record.details))}` : ""}</span></div></div>`);
        renderRecordList("probation-list", store.probations, "No probation records for this employee.", (record) => `
            <div class="record-row"><div><strong>${escapeHtml(dateValue(record.start_date))} – ${escapeHtml(dateValue(record.expected_end_date))}</strong>
            <span>${statusPill(record.status)}${record.extension_reason ? ` · ${escapeHtml(record.extension_reason)}` : ""}</span></div></div>`);
        element("stat-documents").textContent = store.documents.length;
        renderRecordList("document-list", store.documents, "No scanned service-book documents have been uploaded.", (document) => `
            <div class="record-row"><div><strong>${escapeHtml(document.title)}</strong><span>${escapeHtml(dateValue(document.document_date))} · Uploaded ${escapeHtml(dateValue(document.uploaded_at?.slice(0, 10)))}</span></div>
            <a href="/api/scanned-service-books/${encodeURIComponent(document.id)}/download/" target="_blank" rel="noopener">Download</a></div>`);
        element("stat-acr").textContent = store.acrRecords.length;
        renderRecordList("acr-list", store.acrRecords, "No ACR records for this employee.", (record) => `
            <div class="record-row"><div><strong>${escapeHtml(record.rating)} · ${escapeHtml(dateValue(record.period_start))} – ${escapeHtml(dateValue(record.period_end))}</strong>
            <span>${record.details?.notes ? escapeHtml(record.details.notes) : "No notes"} · ${record.is_locked ? "Locked" : "Unlocked"}</span>
            <div class="row-actions">${actionButton(record.is_locked ? "Unlock" : "Lock", record.is_locked ? "acr-unlock" : "acr-lock", record.id)}</div></div></div>`);
        renderRecordList("audit-list", store.audits.slice(0, 12), "No audit entries for this employee.", (entry) => `
            <div class="record-row"><div><strong>${escapeHtml(entry.action.replaceAll("_", " "))} · ${escapeHtml(entry.object_type)}</strong>
            <span>${escapeHtml(dateValue(entry.occurred_at?.slice(0, 10)))} · ${escapeHtml(entry.actor || "System")}</span></div></div>`);
    }

    function renderState(state) {
        store.state = state;
        renderProfile();
        const date = state.as_of_date || "";
        element("historical-state").innerHTML = `<strong>${escapeHtml(dateValue(date))}</strong> · ${escapeHtml(state.designation_name || "No designation")}; `
            + `${escapeHtml(state.pay_scale_code || "No pay scale")}; ${escapeHtml(money(state.current_pay))}; `
            + `${escapeHtml(String(state.employment_status || "—").replaceAll("_", " "))}.`;
    }

    function renderCatalogs() {
        renderRecordList("designation-list", store.designations, "No designations found. Add one to record an appointment.", (item) => `
            <div class="record-row"><div><strong>${escapeHtml(item.code)} · ${escapeHtml(item.name)}</strong>
            <span>Level ${escapeHtml(item.level)}${item.description ? ` · ${escapeHtml(item.description)}` : ""}${item.is_active ? "" : " · Inactive"}</span></div></div>`);
        renderRecordList("pay-scale-list", store.payScales, "No pay scales found. Add one to record an appointment.", (item) => `
            <div class="record-row"><div><strong>${escapeHtml(item.code)} · ${escapeHtml(money(item.min_pay))}–${escapeHtml(money(item.max_pay))}</strong>
            <span>Revision ${escapeHtml(item.revision_order)} · Effective ${escapeHtml(dateValue(item.effective_date))} · Steps ${escapeHtml((item.increment_steps || []).join(", "))}${item.is_active ? "" : " · Inactive"}</span></div></div>`);
    }

    function payloadField(name, label, type = "text", required = true, attrs = "") {
        return `<label>${escapeHtml(label)}<input name="${escapeHtml(name)}" type="${escapeHtml(type)}" ${required ? "required" : ""} ${attrs}></label>`;
    }

    function payloadSelect(name, label, rows, required = true) {
        const options = rows.map((row) => `<option value="${escapeHtml(row.id)}">${escapeHtml(row.code)} · ${escapeHtml(row.name || `${money(row.min_pay)}–${money(row.max_pay)}`)}</option>`).join("");
        return `<label>${escapeHtml(label)}<select name="${escapeHtml(name)}" ${required ? "required" : ""}><option value="">Select ${escapeHtml(label.toLowerCase())}</option>${options}</select></label>`;
    }

    function renderEventPayload(type) {
        const root = element("event-payload");
        const commonScale = payloadSelect("pay_scale_id", "Pay scale", store.payScales.filter((item) => item.is_active));
        const designation = payloadSelect("designation_id", "Designation", store.designations.filter((item) => item.is_active));
        let fields = "";
        if (type === "APPOINTMENT") {
            fields = designation + commonScale + payloadField("pay_amount", "Starting pay", "number", true, 'min="0" step="0.01"')
                + payloadField("society_cen", "Initial society CEN");
        } else if (type === "PROMOTION" || type === "DESIGNATION_CHANGE") {
            fields = designation + payloadSelect("pay_scale_id", "Pay scale (optional)", store.payScales.filter((item) => item.is_active), false)
                + payloadField("pay_amount", "Pay amount (optional)", "number", false, 'min="0" step="0.01"');
        } else if (type === "INCREMENT") {
            fields = commonScale + payloadField("increment_amount", "Increment amount", "number", true, 'min="0" step="0.01"')
                + payloadField("new_pay", "New pay", "number", true, 'min="0" step="0.01"');
        } else if (type === "PAY_REVISION") {
            fields = commonScale + payloadField("pay_amount", "Revised pay", "number", true, 'min="0" step="0.01"');
        } else if (type === "TRANSFER") {
            fields = payloadField("to_society_cen", "Receiving society CEN");
        } else if (type === "PROBATION_EXTENDED") {
            fields = payloadField("new_end_date", "Revised probation end date", "date")
                + `<label class="span-2">Reason<textarea name="reason" rows="2" required></textarea></label>`;
        } else if (type === "LEAVE") {
            fields = payloadField("start_date", "Leave start date", "date") + payloadField("end_date", "Leave end date", "date");
        } else if (["SUSPENSION", "REINSTATEMENT", "TERMINATION"].includes(type)) {
            fields = `<label class="span-2">Reason<textarea name="reason" rows="2" required></textarea></label>`;
        }
        root.innerHTML = fields;
    }

    function readEventPayload(form) {
        const type = form.elements.event_type.value;
        const payload = {};
        elements("input, select, textarea", element("event-payload")).forEach((field) => {
            if (field.value !== "") payload[field.name] = field.value;
        });
        if (["PROMOTION", "DESIGNATION_CHANGE"].includes(type)) {
            if (!payload.pay_scale_id) delete payload.pay_scale_id;
            if (!payload.pay_amount) delete payload.pay_amount;
        }
        return payload;
    }

    function loadProfileIntoForm(profile) {
        const form = element("profile-form");
        form.reset();
        form.elements.employee_cen.value = profile?.employee_cen || "";
        form.elements.employee_cen.readOnly = Boolean(profile);
        form.elements.full_name.value = profile?.full_name || "";
        form.elements.date_of_birth.value = profile?.date_of_birth || "";
        form.elements.email.value = profile?.email || "";
        form.elements.phone.value = profile?.phone || "";
        form.elements.department.value = profile?.department || "";
        element("profile-dialog-title").textContent = profile ? "Edit employee details" : "Add employee";
        element("profile-dialog").showModal();
    }

    async function loadEmployee(cen) {
        store.employeeCen = cen;
        store.profile = store.profiles.find((profile) => profile.employee_cen === cen) || null;
        if (!cen) {
            store.state = null;
            store.events = [];
            store.workflows = [];
            store.probations = [];
            store.recruitments = [];
            store.documents = [];
            store.acrRecords = [];
            store.audits = [];
            renderProfile();
            renderEvents();
            renderRecords();
            ["stat-events", "stat-pending", "stat-documents", "stat-acr"].forEach((id) => { element(id).textContent = "—"; });
            element("event-timeline").textContent = "Select an employee to load their service history.";
            element("approval-list").textContent = "Select an employee to review drafts and approvals.";
            element("historical-state").textContent = "Select an employee to view their state on a past date.";
            setEmployeeFormState();
            return;
        }
        setEmployeeFormState();
        const query = encodeURIComponent(cen);
        const today = new Date().toISOString().slice(0, 10);
        element("history-date").value = today;
        const [events, workflows, probations, recruitments, documents, acrRecords, audits, state] = await Promise.all([
            request(`service-events/?employee_cen=${query}`),
            request(`transfers/?employee_cen=${query}`),
            request(`probation-records/?employee_cen=${query}`),
            request(`recruitment-records/?employee_cen=${query}`),
            request(`scanned-service-books/?employee_cen=${query}`),
            request(`acr-records/?employee_cen=${query}`),
            request(`audit-history/?employee_cen=${query}`),
            request(`service-state/?employee_cen=${query}&date=${today}`),
        ]);
        store.events = events;
        store.workflows = workflows;
        store.probations = probations;
        store.recruitments = recruitments;
        store.documents = documents;
        store.acrRecords = acrRecords;
        store.audits = audits;
        renderState(state);
        renderEvents();
        renderRecords();
        showNotice(`Loaded service-book records for ${store.profile?.full_name || cen}.`, "info");
    }

    async function reloadSelectedEmployee() {
        await loadEmployee(store.employeeCen);
    }

    async function performAction(action, id) {
        const event = store.events.find((item) => String(item.id) === String(id));
        if (action === "cancel") {
            const reason = window.prompt("Enter the reason for cancelling this service event:");
            if (reason === null) return;
            if (!reason.trim()) {
                showNotice("A cancellation reason is required.", "error");
                return;
            }
            await request(`service-events/${id}/cancel/`, { method: "POST", body: JSON.stringify({ reason }) });
        } else if (["submit", "approve", "lock", "unlock"].includes(action)) {
            await request(`service-events/${id}/${action}/`, { method: "POST", body: JSON.stringify({}) });
        } else if (action === "relieve" || action === "accept") {
            await request(`transfers/${id}/${action}/`, { method: "POST", body: JSON.stringify({}) });
        } else if (action === "acr-lock" || action === "acr-unlock") {
            const operation = action === "acr-lock" ? "lock" : "unlock";
            await request(`acr-records/${id}/${operation}/`, { method: "POST", body: JSON.stringify({}) });
        } else {
            throw new Error("Unsupported service-book action.");
        }
        await reloadSelectedEmployee();
        showNotice(`${action.replaceAll("-", " ")} completed${event ? ` for ${eventTypes[event.event_type] || event.event_type}` : ""}.`);
    }

    function bindForms() {
        picker.addEventListener("change", async () => {
            try {
                await loadEmployee(picker.value);
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("history-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!store.employeeCen) return;
            const requestedDate = element("history-date").value;
            try {
                const state = await request(`service-state/?employee_cen=${encodeURIComponent(store.employeeCen)}&date=${encodeURIComponent(requestedDate)}`);
                renderState(state);
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        elements("[data-open-profile]").forEach((button) => button.addEventListener("click", () => loadProfileIntoForm(null)));
        element("edit-profile").addEventListener("click", () => loadProfileIntoForm(store.profile));
        elements("[data-close-dialog]").forEach((button) => button.addEventListener("click", () => element("profile-dialog").close()));
        elements("[data-scroll]").forEach((button) => button.addEventListener("click", () => {
            element(button.dataset.scroll).scrollIntoView({ behavior: "smooth", block: "start" });
        }));
        element("event-timeline").addEventListener("click", async (event) => {
            const button = event.target.closest("[data-action]");
            if (!button) return;
            button.disabled = true;
            try {
                await performAction(button.dataset.action, button.dataset.id);
            } catch (error) {
                showNotice(error.message, "error");
            } finally {
                button.disabled = false;
            }
        });
        element("acr-list").addEventListener("click", async (event) => {
            const button = event.target.closest("[data-action]");
            if (!button) return;
            button.disabled = true;
            try {
                await performAction(button.dataset.action, button.dataset.id);
            } catch (error) {
                showNotice(error.message, "error");
            } finally {
                button.disabled = false;
            }
        });
        element("profile-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const data = Object.fromEntries(new FormData(form).entries());
            const edit = Boolean(form.elements.employee_cen.readOnly);
            if (!data.date_of_birth) data.date_of_birth = null;
            try {
                const saved = await request(edit
                    ? `employee-profiles/${store.profile.id}/`
                    : "employee-profiles/", {
                    method: edit ? "PATCH" : "POST",
                    body: JSON.stringify(data),
                });
                store.employeeCen = saved.employee_cen;
                await loadProfiles();
                picker.value = saved.employee_cen;
                await loadEmployee(saved.employee_cen);
                element("profile-dialog").close();
                showNotice(`Employee details ${edit ? "updated" : "created"} successfully.`);
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("event-form").elements.event_type.addEventListener("change", (event) => renderEventPayload(event.target.value));
        element("event-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const payload = {
                employee_cen: store.employeeCen,
                event_type: form.elements.event_type.value,
                effective_date: form.elements.effective_date.value,
                payload: readEventPayload(form),
            };
            try {
                await request("service-events/", { method: "POST", body: JSON.stringify(payload) });
                form.reset();
                element("event-payload").innerHTML = "";
                await reloadSelectedEmployee();
                showNotice("Service event saved as a draft.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("recruitment-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = Object.fromEntries(new FormData(form).entries());
            const notes = values.details.trim();
            delete values.details;
            values.details = notes ? { notes } : {};
            values.employee_cen = store.employeeCen;
            try {
                await request("recruitment-records/", { method: "POST", body: JSON.stringify(values) });
                form.reset();
                await reloadSelectedEmployee();
                showNotice("Recruitment and joining record saved.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("probation-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const values = Object.fromEntries(new FormData(event.currentTarget).entries());
            values.employee_cen = store.employeeCen;
            try {
                await request("probation-records/", { method: "POST", body: JSON.stringify(values) });
                event.currentTarget.reset();
                await reloadSelectedEmployee();
                showNotice("Probation record saved.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("document-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = new FormData(form);
            values.set("employee_cen", store.employeeCen);
            if (!values.get("document_date")) values.delete("document_date");
            try {
                await request("scanned-service-books/", { method: "POST", body: values });
                form.reset();
                await reloadSelectedEmployee();
                showNotice("Scanned service-book document uploaded.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("acr-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = Object.fromEntries(new FormData(form).entries());
            const notes = values.details.trim();
            delete values.details;
            values.details = notes ? { notes } : {};
            values.employee_cen = store.employeeCen;
            try {
                await request("acr-records/", { method: "POST", body: JSON.stringify(values) });
                form.reset();
                await reloadSelectedEmployee();
                showNotice("ACR record saved.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("designation-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = Object.fromEntries(new FormData(form).entries());
            values.level = Number(values.level);
            values.is_active = true;
            try {
                await request("designations/", { method: "POST", body: JSON.stringify(values) });
                form.reset();
                await loadCatalogs();
                renderEventPayload(element("event-form").elements.event_type.value);
                showNotice("Designation added to the catalog.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
        element("pay-scale-form").addEventListener("submit", async (event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = Object.fromEntries(new FormData(form).entries());
            const stepValues = values.increment_steps.split(",").map((step) => step.trim());
            const steps = stepValues.map(Number);
            if (!steps.length || stepValues.some((step) => !step) || steps.some((step) => !Number.isFinite(step))) {
                showNotice("Enter one or more numeric increment steps separated by commas.", "error");
                return;
            }
            values.min_pay = Number(values.min_pay);
            values.max_pay = Number(values.max_pay);
            values.revision_order = Number(values.revision_order);
            values.increment_steps = steps;
            values.is_active = true;
            try {
                await request("pay-scales/", { method: "POST", body: JSON.stringify(values) });
                form.reset();
                await loadCatalogs();
                renderEventPayload(element("event-form").elements.event_type.value);
                showNotice("Pay scale added to the catalog.");
            } catch (error) {
                showNotice(error.message, "error");
            }
        });
    }

    async function loadProfiles() {
        store.profiles = await request("employee-profiles/");
        renderProfilePicker();
    }

    async function loadCatalogs() {
        const [designations, payScales] = await Promise.all([
            request("designations/"),
            request("pay-scales/"),
        ]);
        store.designations = designations;
        store.payScales = payScales;
        renderCatalogs();
    }

    async function initialize() {
        element("history-date").value = new Date().toISOString().slice(0, 10);
        bindForms();
        if (!staffEnabled) {
            elements("form button[type=submit], #edit-profile").forEach((button) => { button.disabled = true; });
            showNotice("Sign in with a staff account to access service-book records.", "info");
            return;
        }
        try {
            const [profiles, designations, payScales] = await Promise.all([
                request("employee-profiles/"),
                request("designations/"),
                request("pay-scales/"),
            ]);
            store.profiles = profiles;
            store.designations = designations;
            store.payScales = payScales;
            renderCatalogs();
            renderProfilePicker();
            const date = new Date();
            element("history-date").value = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
            if (store.profiles.length) {
                picker.value = store.profiles[0].employee_cen;
                await loadEmployee(picker.value);
            } else {
                showNotice("No employee profiles exist yet. Add an employee to start a real service-book record.", "info");
            }
        } catch (error) {
            showNotice(error.message, "error");
        }
    }

    initialize();
})();
