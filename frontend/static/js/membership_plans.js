/* Membership plan API client. Configure API_BASE_URL if the FastAPI server is hosted elsewhere. */
const API_BASE_URL = window.MEMBERSHIP_PLANS_API_BASE_URL || "http://127.0.0.1:8000";
const PLANS_ENDPOINT = `${API_BASE_URL}/membership-plans/`;

const plansBody = document.querySelector("#plans-body");
const searchInput = document.querySelector("#search-input");
const resultsLabel = document.querySelector("#results-label");
const dialog = document.querySelector("#plan-dialog");
const form = document.querySelector("#plan-form");
const formError = document.querySelector("#form-error");
let plans = [];
let editingId = null;
let toastTimeout;

async function request(path = "", options = {}) {
  const response = await fetch(`${PLANS_ENDPOINT}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return body;
}

// GET /membership-plans/ — retrieve the plan catalog.
async function getAllPlans() { return request(); }

// GET /membership-plans/{plan_id} — retrieve the latest details for a plan.
async function getPlan(planId) { return request(encodeURIComponent(planId)); }

// POST /membership-plans/ — create a plan.
async function addPlan(payload) { return request("", { method: "POST", body: JSON.stringify(payload) }); }

// PATCH /membership-plans/{plan_id} — update supplied plan fields.
async function updatePlan(planId, payload) {
  return request(encodeURIComponent(planId), { method: "PATCH", body: JSON.stringify(payload) });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value) || 0);
}

function showToast(message, isError = false) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3200);
}

function renderPlans() {
  const query = searchInput.value.trim().toLowerCase();
  const filtered = plans.filter((plan) => `${plan.plan_id} ${plan.duration}`.toLowerCase().includes(query));
  document.querySelector("#total-count").textContent = plans.length;
  const lowest = plans.length ? Math.min(...plans.map((plan) => Number(plan.price))) : null;
  document.querySelector("#starting-price").textContent = lowest === null ? "—" : money(lowest);
  const longest = plans.length ? Math.max(...plans.map((plan) => Number(plan.duration))) : null;
  document.querySelector("#longest-term").textContent = longest === null ? "—" : `${longest} ${longest === 1 ? "month" : "months"}`;
  resultsLabel.textContent = `Showing ${filtered.length} of ${plans.length} ${plans.length === 1 ? "plan" : "plans"}`;

  if (!filtered.length) {
    plansBody.innerHTML = `<tr><td colspan="7" class="table-message">${plans.length ? "No plans match your search." : "No plans yet. Add your first membership plan to get started."}</td></tr>`;
    return;
  }

  plansBody.innerHTML = filtered.map((plan) => {
    const monthlyPrice = Number(plan.price) / Number(plan.duration);
    return `<tr>
      <td><div class="plan-label"><span class="plan-badge">◇</span><span><span class="plan-id">${escapeHtml(plan.plan_id)}</span><span class="member-sub">Membership plan</span></span></div></td>
      <td class="plan-duration">${escapeHtml(plan.duration)} ${Number(plan.duration) === 1 ? "month" : "months"}</td>
      <td><span class="price-main">${escapeHtml(money(plan.price))}</span></td>
      <td><span class="${Number(plan.group_discount) ? "discount-value" : "discount-none"}">${escapeHtml(plan.group_discount)}%</span></td>
      <td><span class="${Number(plan.seasonal_discount) ? "discount-value" : "discount-none"}">${escapeHtml(plan.seasonal_discount)}%</span></td>
      <td class="unit-price">${escapeHtml(money(monthlyPrice))}<span class="price-caption">per month</span></td>
      <td class="row-actions plan-actions"><button class="action-button" aria-label="Actions for plan ${escapeHtml(plan.plan_id)}" data-action="menu" data-id="${escapeHtml(plan.plan_id)}">···</button></td>
    </tr>`;
  }).join("");
}

async function loadPlans() {
  plansBody.innerHTML = '<tr><td colspan="7" class="table-message"><span class="spinner"></span> Loading plans…</td></tr>';
  try {
    plans = await getAllPlans();
    renderPlans();
  } catch (error) {
    plansBody.innerHTML = `<tr><td colspan="7" class="table-message">Could not load plans: ${escapeHtml(error.message)}. Check that the API is running.</td></tr>`;
    resultsLabel.textContent = "Plan catalog unavailable";
    showToast(error.message, true);
  }
}

function openCreateDialog() {
  editingId = null;
  form.reset();
  form.elements.plan_id.disabled = false;
  document.querySelector("#plan-id-wrap").hidden = false;
  document.querySelector("#dialog-eyebrow").textContent = "PLAN DETAILS";
  document.querySelector("#dialog-title").textContent = "Add membership plan";
  document.querySelector("#dialog-copy").textContent = "Create a new option for your membership catalog.";
  document.querySelector("#save-plan").textContent = "Save plan";
  formError.textContent = "";
  dialog.showModal();
}

async function openEditDialog(planId) {
  try {
    const plan = await getPlan(planId);
    editingId = planId;
    form.reset();
    for (const field of ["duration", "price", "group_discount", "seasonal_discount"]) form.elements[field].value = plan[field] ?? "";
    form.elements.plan_id.value = planId;
    form.elements.plan_id.disabled = true;
    document.querySelector("#plan-id-wrap").hidden = true;
    document.querySelector("#dialog-eyebrow").textContent = `PLAN ID · ${planId}`;
    document.querySelector("#dialog-title").textContent = "Edit membership plan";
    document.querySelector("#dialog-copy").textContent = "Update the plan duration, pricing and discounts.";
    document.querySelector("#save-plan").textContent = "Save changes";
    formError.textContent = "";
    dialog.showModal();
  } catch (error) {
    showToast(error.message, true);
  }
}

function formPayload() {
  const data = Object.fromEntries(new FormData(form).entries());
  data.duration = Number(data.duration);
  data.price = Number(data.price);
  data.group_discount = Number(data.group_discount);
  data.seasonal_discount = Number(data.seasonal_discount);
  return data;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const saveButton = document.querySelector("#save-plan");
  saveButton.disabled = true;
  formError.textContent = "";
  try {
    const payload = formPayload();
    if (editingId) {
      const { duration, price, group_discount, seasonal_discount } = payload;
      await updatePlan(editingId, { duration, price, group_discount, seasonal_discount });
      showToast("Membership plan updated.");
    } else {
      await addPlan(payload);
      showToast("Membership plan added to the catalog.");
    }
    dialog.close();
    await loadPlans();
  } catch (error) {
    formError.textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

plansBody.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const planId = button.dataset.id;
  if (button.dataset.action === "menu") {
    document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
    const menu = document.createElement("div");
    menu.className = "action-menu";
    menu.innerHTML = `<button type="button" data-action="edit" data-id="${escapeHtml(planId)}">View / edit plan</button>`;
    button.closest("td").append(menu);
  } else if (button.dataset.action === "edit") {
    document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
    await openEditDialog(planId);
  }
});

document.querySelector("#add-plan-button").addEventListener("click", openCreateDialog);
document.querySelector("#refresh-button").addEventListener("click", loadPlans);
document.querySelector("#clear-search").addEventListener("click", () => { searchInput.value = ""; renderPlans(); });
searchInput.addEventListener("input", renderPlans);
document.querySelectorAll(".close-dialog, .cancel-dialog").forEach((button) => button.addEventListener("click", () => dialog.close()));
document.addEventListener("click", (event) => {
  if (!event.target.closest(".plan-actions")) document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); searchInput.focus(); }
});
document.querySelector("#today-label").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" }).format(new Date());

loadPlans();
