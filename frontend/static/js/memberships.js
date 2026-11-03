/* Membership registration API client. Configure API_BASE_URL if FastAPI is hosted elsewhere. */
const API_BASE_URL = window.MEMBERSHIPS_API_BASE_URL || "http://127.0.0.1:8000";
const MEMBERSHIPS_ENDPOINT = `${API_BASE_URL}/memberships/`;
const MEMBERS_ENDPOINT = `${API_BASE_URL}/members/`;
const PLANS_ENDPOINT = `${API_BASE_URL}/membership-plans/`;

const form = document.querySelector("#membership-form");
const memberSelect = document.querySelector("#member-select");
const planSelect = document.querySelector("#plan-select");
const startDateInput = document.querySelector("#start-date");
const formError = document.querySelector("#form-error");
let members = [];
let plans = [];
let toastTimeout;

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
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

// GET /members/ — populate the member selector; inactive profiles cannot register.
async function getActiveMembers() {
  const result = await apiRequest(MEMBERS_ENDPOINT);
  return result.filter((member) => member.member_status === "Active");
}

// GET /membership-plans/ — populate plan selector and show price and duration.
async function getPlans() { return apiRequest(PLANS_ENDPOINT); }

// POST /memberships/ — backend generates membership/payment IDs and calculates end date/amount.
async function registerMembership(payload) {
  return apiRequest(MEMBERSHIPS_ENDPOINT, { method: "POST", body: JSON.stringify(payload) });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value) || 0);
}

function localDate(date) {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
}

function formatDate(dateString) {
  if (!dateString) return "—";
  return new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric" }).format(new Date(`${dateString}T00:00:00`));
}

function calculateEndDate(startString, duration) {
  const [year, month, day] = startString.split("-").map(Number);
  const zeroMonth = month - 1 + Number(duration);
  const endYear = year + Math.floor(zeroMonth / 12);
  const endMonth = ((zeroMonth % 12) + 12) % 12;
  const lastDay = new Date(endYear, endMonth + 1, 0).getDate();
  const sameDay = Math.min(day, lastDay);
  const endDate = new Date(endYear, endMonth, sameDay);
  endDate.setDate(endDate.getDate() - 1);
  return localDate(endDate);
}

function showToast(message, isError = false) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3200);
}

function populateSelect(select, placeholder, options) {
  select.innerHTML = `<option value="">${escapeHtml(placeholder)}</option>${options}`;
}

function updateSummary() {
  const plan = plans.find((item) => String(item.plan_id) === planSelect.value);
  const start = startDateInput.value;
  const details = document.querySelector("#summary-details");
  const empty = document.querySelector("#summary-empty");
  if (!plan) {
    details.hidden = true;
    empty.hidden = false;
    document.querySelector("#plan-help").textContent = "Choose a plan to review its duration and price.";
    return;
  }
  details.hidden = false;
  empty.hidden = true;
  document.querySelector("#summary-plan-name").textContent = `${plan.plan_id} · ${plan.duration} ${Number(plan.duration) === 1 ? "month" : "months"}`;
  document.querySelector("#summary-duration").textContent = `${plan.duration} ${Number(plan.duration) === 1 ? "month" : "months"}`;
  document.querySelector("#summary-start").textContent = formatDate(start);
  document.querySelector("#summary-end").textContent = start ? formatDate(calculateEndDate(start, plan.duration)) : "—";
  document.querySelector("#summary-price").textContent = money(plan.price);
  document.querySelector("#plan-help").textContent = `${plan.duration} month${Number(plan.duration) === 1 ? "" : "s"} · ${money(plan.price)}`;
}

async function loadOptions() {
  memberSelect.disabled = true;
  planSelect.disabled = true;
  try {
    [members, plans] = await Promise.all([getActiveMembers(), getPlans()]);
    populateSelect(memberSelect, members.length ? "Select a member" : "No active members available", members.map((member) => `<option value="${escapeHtml(member.member_id)}">${escapeHtml(member.member_name)} · ${escapeHtml(member.member_id)}</option>`).join(""));
    populateSelect(planSelect, plans.length ? "Select a membership plan" : "No plans available", plans.map((plan) => `<option value="${escapeHtml(plan.plan_id)}">${escapeHtml(plan.plan_id)} · ${escapeHtml(plan.duration)} mo · ${escapeHtml(money(plan.price))}</option>`).join(""));
    if (!members.length) showToast("Add an active member before registering a membership.", true);
    if (!plans.length) showToast("Add a membership plan before registering.", true);
  } catch (error) {
    populateSelect(memberSelect, "Could not load members", "");
    populateSelect(planSelect, "Could not load plans", "");
    formError.textContent = `Could not load registration options: ${error.message}. Check that the API is running.`;
  } finally {
    memberSelect.disabled = false;
    planSelect.disabled = false;
    updateSummary();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.textContent = "";
  if (!form.reportValidity()) return;
  const submitButton = document.querySelector("#register-button");
  submitButton.disabled = true;
  const payload = Object.fromEntries(new FormData(form).entries());
  try {
    const result = await registerMembership(payload);
    const member = members.find((item) => String(item.member_id) === payload.member_id);
    document.querySelector("#result-copy").textContent = `${member?.member_name || payload.member_id} is registered through ${formatDate(result.membership.end_date)}. Payment of ${money(result.payment.amount)} recorded.`;
    document.querySelector("#result-membership-id").textContent = result.membership.membership_id;
    document.querySelector("#result-payment-id").textContent = result.payment.payment_id;
    document.querySelector("#result-payment-mode").textContent = result.payment.payment_mode;
    document.querySelector("#result-card").hidden = false;
    document.querySelector("#result-card").scrollIntoView({ behavior: "smooth", block: "nearest" });
    showToast("Membership registered successfully.");
  } catch (error) {
    formError.textContent = error.message;
    showToast(error.message, true);
  } finally {
    submitButton.disabled = false;
  }
});

planSelect.addEventListener("change", updateSummary);
startDateInput.addEventListener("change", updateSummary);
document.querySelector("#new-registration").addEventListener("click", () => {
  form.reset();
  startDateInput.value = localDate(new Date());
  document.querySelector("#result-card").hidden = true;
  formError.textContent = "";
  updateSummary();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
document.querySelector("#today-label").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" }).format(new Date());
startDateInput.value = localDate(new Date());
loadOptions();
