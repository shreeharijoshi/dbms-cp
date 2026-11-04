/* Members page API client. Configure API_BASE_URL if the FastAPI server is hosted elsewhere. */
const API_BASE_URL = window.MEMBERS_API_BASE_URL || "http://127.0.0.1:8000";
const MEMBERS_ENDPOINT = `${API_BASE_URL}/members/`;

const membersBody = document.querySelector("#members-body");
const searchInput = document.querySelector("#search-input");
const statusFilter = document.querySelector("#status-filter");
const resultsLabel = document.querySelector("#results-label");
const dialog = document.querySelector("#member-dialog");
const form = document.querySelector("#member-form");
const formError = document.querySelector("#form-error");
let members = [];
let editingId = null;
let toastTimeout;

async function request(path = "", options = {}) {
  const response = await fetch(`${MEMBERS_ENDPOINT}${path}`, {
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

// GET /members/ — retrieve all members.
async function getAllMembers() {
  return request();
}

// GET /members/{member_id} — retrieve a single member by ID.
async function getMember(memberId) {
  return request(encodeURIComponent(memberId));
}

// POST /members/ — create a member.
async function addMember(payload) {
  return request("", { method: "POST", body: JSON.stringify(payload) });
}

// PATCH /members/{member_id} — update only the supplied member fields.
async function updateMember(memberId, payload) {
  return request(encodeURIComponent(memberId), { method: "PATCH", body: JSON.stringify(payload) });
}

// PATCH /members/{member_id}/deactivate — deactivate an active member.
async function deactivateMember(memberId) {
  return request(`${encodeURIComponent(memberId)}/deactivate`, { method: "PATCH" });
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function initials(name) {
  return String(name || "Member").trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function showToast(message, isError = false) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.toggle("error", isError);
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3200);
}

function renderMembers() {
  const query = searchInput.value.trim().toLowerCase();
  const selectedStatus = statusFilter.value;
  const filtered = members.filter((member) => {
    const matchesQuery = !query || [member.member_name, member.member_id, member.contact].some((value) => String(value || "").toLowerCase().includes(query));
    const matchesStatus = selectedStatus === "all" || member.member_status === selectedStatus;
    return matchesQuery && matchesStatus;
  });

  document.querySelector("#total-count").textContent = members.length;
  document.querySelector("#active-count").textContent = members.filter((member) => member.member_status === "Active").length;
  document.querySelector("#pt-count").textContent = members.filter((member) => String(member.PT || "").toLowerCase() === "yes").length;
  resultsLabel.textContent = `Showing ${filtered.length} of ${members.length} ${members.length === 1 ? "member" : "members"}`;

  if (!filtered.length) {
    membersBody.innerHTML = `<tr><td colspan="7" class="table-message">${members.length ? "No members match your search." : "No members yet. Add your first member to get started."}</td></tr>`;
    return;
  }

  membersBody.innerHTML = filtered.map((member) => {
    const active = member.member_status === "Active";
    return `<tr>
      <td><div class="member-cell"><span class="member-avatar">${escapeHtml(initials(member.member_name))}</span><span><span class="member-name">${escapeHtml(member.member_name)}</span><span class="member-sub">Joined ${escapeHtml(member.dob || "—")}</span></span></div></td>
      <td class="id-cell">${escapeHtml(member.member_id)}</td>
      <td>${escapeHtml(member.contact || "—")}</td>
      <td>${escapeHtml(member.gender || "—")}</td>
      <td class="${String(member.PT).toLowerCase() === "yes" ? "pt-yes" : "pt-no"}">${escapeHtml(member.PT || "No")}</td>
      <td><span class="status ${active ? "" : "inactive"}">${escapeHtml(member.member_status || "Unknown")}</span></td>
      <td class="row-actions"><button class="action-button" aria-label="Actions for ${escapeHtml(member.member_name)}" data-action="menu" data-id="${escapeHtml(member.member_id)}">···</button></td>
    </tr>`;
  }).join("");
}

async function loadMembers() {
  membersBody.innerHTML = '<tr><td colspan="7" class="table-message"><span class="spinner"></span> Loading members…</td></tr>';
  try {
    members = await getAllMembers();
    renderMembers();
  } catch (error) {
    membersBody.innerHTML = `<tr><td colspan="7" class="table-message">Could not load members: ${escapeHtml(error.message)}. Check that the API is running.</td></tr>`;
    resultsLabel.textContent = "Directory unavailable";
    showToast(error.message, true);
  }
}

function openCreateDialog() {
  editingId = null;
  form.reset();
  form.elements.member_id.disabled = false;
  document.querySelector("#member-id-wrap").hidden = false;
  document.querySelector("#dialog-eyebrow").textContent = "MEMBER PROFILE";
  document.querySelector("#dialog-title").textContent = "Add member";
  document.querySelector("#dialog-copy").textContent = "Add a profile to your member directory.";
  document.querySelector("#save-member").textContent = "Save member";
  formError.textContent = "";
  dialog.showModal();
}

async function openEditDialog(memberId) {
  try {
    // Use the dedicated detail route so the form always edits the latest server data.
    const member = await getMember(memberId);
    editingId = memberId;
    form.reset();
    for (const field of ["member_name", "gender", "height", "weight", "contact", "dob", "PT"]) {
      form.elements[field].value = member[field] ?? "";
    }
    form.elements.member_id.value = memberId;
    form.elements.member_id.disabled = true;
    document.querySelector("#member-id-wrap").hidden = true;
    document.querySelector("#dialog-eyebrow").textContent = `MEMBER ID · ${memberId}`;
    document.querySelector("#dialog-title").textContent = "Edit member";
    document.querySelector("#dialog-copy").textContent = "Update the member profile details below.";
    document.querySelector("#save-member").textContent = "Save changes";
    formError.textContent = "";
    dialog.showModal();
  } catch (error) {
    showToast(error.message, true);
  }
}

function formPayload() {
  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  payload.height = Number(payload.height);
  payload.weight = Number(payload.weight);
  return payload;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const saveButton = document.querySelector("#save-member");
  saveButton.disabled = true;
  formError.textContent = "";
  try {
    if (editingId) {
      const { member_name, gender, height, weight, contact, dob, PT } = formPayload();
      await updateMember(editingId, { member_name, gender, height, weight, contact, dob, PT });
      showToast("Member profile updated.");
    } else {
      await addMember(formPayload());
      showToast("Member added to the directory.");
    }
    dialog.close();
    await loadMembers();
  } catch (error) {
    formError.textContent = error.message;
  } finally {
    saveButton.disabled = false;
  }
});

membersBody.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) return;
  const memberId = button.dataset.id;
  const member = members.find((item) => String(item.member_id) === memberId);
  if (button.dataset.action === "menu") {
    document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
    const cell = button.closest("td");
    const menu = document.createElement("div");
    menu.className = "action-menu";
    menu.innerHTML = `<button type="button" data-action="edit" data-id="${escapeHtml(memberId)}">View / edit profile</button>${member?.member_status === "Active" ? `<button type="button" class="danger" data-action="deactivate" data-id="${escapeHtml(memberId)}">Deactivate member</button>` : ""}`;
    cell.append(menu);
  } else if (button.dataset.action === "edit") {
    document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
    await openEditDialog(memberId);
  } else if (button.dataset.action === "deactivate") {
    document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
    try {
      await deactivateMember(memberId);
      showToast("Member deactivated.");
      await loadMembers();
    } catch (error) {
      showToast(error.message, true);
    }
  }
});

document.querySelector("#add-member-button").addEventListener("click", openCreateDialog);
document.querySelector("#refresh-button").addEventListener("click", loadMembers);
document.querySelector("#clear-filters").addEventListener("click", () => { searchInput.value = ""; statusFilter.value = "all"; renderMembers(); });
searchInput.addEventListener("input", renderMembers);
statusFilter.addEventListener("change", renderMembers);
document.querySelectorAll(".close-dialog, .cancel-dialog").forEach((button) => button.addEventListener("click", () => dialog.close()));
document.addEventListener("click", (event) => {
  if (!event.target.closest(".row-actions")) document.querySelectorAll(".action-menu").forEach((menu) => menu.remove());
});
document.addEventListener("keydown", (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); searchInput.focus(); }
});
document.querySelector("#today-label").textContent = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric", year: "numeric" }).format(new Date());

loadMembers();
