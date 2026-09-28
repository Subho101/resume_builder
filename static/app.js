let resume = null;

const $ = (id) => document.getElementById(id);
const SECTION_LABELS = {
  summary: "Professional Summary",
  skills: "Technical Skills",
  experience: "Experience",
  education: "Education",
};
const SECTION_KEYS = Object.keys(SECTION_LABELS);

function showToast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => t.classList.remove("show"), 2200);
}

function normalizeSectionOrder(order) {
  const incoming = Array.isArray(order) ? order : [];
  return [...new Set(incoming.filter(key => SECTION_KEYS.includes(key)))].concat(
    SECTION_KEYS.filter(key => !incoming.includes(key))
  );
}

function setPersonal() {
  const p = resume.personal || {};
  $("name").value = p.name || "";
  $("location").value = p.location || "";
  $("phone").value = p.phone || "";
  $("email").value = p.email || "";
  $("linkedin_url").value = p.linkedin_url || "";
  $("linkedin_text").value = p.linkedin_text || "";
  $("summary").value = resume.summary || "";
}

function renderSectionOrder() {
  const container = $("sectionOrder");
  container.innerHTML = "";
  resume.section_order = normalizeSectionOrder(resume.section_order);

  resume.section_order.forEach((key, index) => {
    const item = document.createElement("div");
    item.className = "section-order-item";
    item.draggable = true;
    item.dataset.section = key;
    item.innerHTML = `
      <span class="drag-handle" title="Drag to reorder">⋮⋮</span>
      <span class="section-order-name">${SECTION_LABELS[key]}</span>
      <span class="section-order-actions">
        <button class="tiny" type="button" title="Move up" ${index === 0 ? "disabled" : ""}>↑</button>
        <button class="tiny" type="button" title="Move down" ${index === resume.section_order.length - 1 ? "disabled" : ""}>↓</button>
      </span>
    `;

    const [up, down] = item.querySelectorAll("button");
    up.addEventListener("click", () => moveSection(index, -1));
    down.addEventListener("click", () => moveSection(index, 1));

    item.addEventListener("dragstart", (event) => {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", key);
      item.classList.add("dragging");
    });
    item.addEventListener("dragend", () => item.classList.remove("dragging"));
    item.addEventListener("dragover", (event) => {
      event.preventDefault();
      item.classList.add("drag-over");
    });
    item.addEventListener("dragleave", () => item.classList.remove("drag-over"));
    item.addEventListener("drop", (event) => {
      event.preventDefault();
      item.classList.remove("drag-over");
      const source = event.dataTransfer.getData("text/plain");
      reorderSection(source, key);
    });

    container.appendChild(item);
  });
}

function moveSection(index, delta) {
  const next = index + delta;
  if (next < 0 || next >= resume.section_order.length) return;
  const order = [...resume.section_order];
  [order[index], order[next]] = [order[next], order[index]];
  resume.section_order = order;
  renderSectionOrder();
  markUnsaved();
}

function reorderSection(source, target) {
  if (!source || !target || source === target) return;
  const order = [...resume.section_order];
  const from = order.indexOf(source);
  const to = order.indexOf(target);
  if (from < 0 || to < 0) return;
  order.splice(from, 1);
  order.splice(to, 0, source);
  resume.section_order = order;
  renderSectionOrder();
  markUnsaved();
}

function moveCard(containerId, index, delta) {
  const container = $(containerId);
  const cards = [...container.children];
  const next = index + delta;
  if (next < 0 || next >= cards.length) return;
  if (delta < 0) container.insertBefore(cards[index], cards[next]);
  else container.insertBefore(cards[index], cards[next].nextSibling);
  markUnsaved();
  refreshCardControls(containerId);
}

function refreshCardControls(containerId) {
  const container = $(containerId);
  [...container.children].forEach((card, index) => {
    const up = card.querySelector(':scope > .card-top .move-up, :scope > .reorder-actions .move-up');
    const down = card.querySelector(':scope > .card-top .move-down, :scope > .reorder-actions .move-down');
    if (up) up.disabled = index === 0;
    if (down) down.disabled = index === container.children.length - 1;
  });
}

function enableCardReordering(containerId) {
  const container = $(containerId);
  if (container.dataset.reorderReady === '1') return;
  container.dataset.reorderReady = '1';

  container.addEventListener('dragstart', (event) => {
    const handle = event.target.closest('.card-drag-handle');
    if (!handle) { event.preventDefault(); return; }
    const card = handle.closest('.item-card');
    card.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', 'card');
  });

  container.addEventListener('dragend', (event) => {
    const card = event.target.closest('.item-card');
    if (card) card.classList.remove('dragging');
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    refreshCardControls(containerId);
  });

  container.addEventListener('dragover', (event) => {
    event.preventDefault();
    const dragging = container.querySelector('.item-card.dragging');
    const target = event.target.closest('.item-card');
    if (!dragging || !target || dragging === target || !container.contains(target)) return;
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    target.classList.add('drag-over');
    const rect = target.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    if (after) container.insertBefore(dragging, target.nextSibling);
    else container.insertBefore(dragging, target);
  });

  container.addEventListener('drop', (event) => {
    event.preventDefault();
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    markUnsaved();
    refreshCardControls(containerId);
  });
}

function addSkill(skill = {category:"", items:""}) {
  const node = document.importNode($("skillTemplate").content, true);
  node.querySelector(".skill-category").value = skill.category || "";
  node.querySelector(".skill-items").value = skill.items || "";
  $("skills").appendChild(node);
  refreshCardControls("skills");
}

function addBullet(button, text = "") {
  const node = document.importNode($("bulletTemplate").content, true);
  node.querySelector(".exp-bullet").value = text;
  button.closest(".experience-card").querySelector(".bullets").appendChild(node);
  enableBulletReordering(button.closest(".experience-card").querySelector(".bullets"));
  refreshBulletControls(button.closest(".experience-card").querySelector(".bullets"));
}

function refreshBulletControls(container) {
  [...container.children].forEach((row, index) => {
    const up = row.querySelector('.move-up');
    const down = row.querySelector('.move-down');
    if (up) up.disabled = index === 0;
    if (down) down.disabled = index === container.children.length - 1;
  });
}

function moveBullet(button, delta) {
  const row = button.closest('.bullet-row');
  const container = row.parentElement;
  const rows = [...container.children];
  const index = rows.indexOf(row);
  const next = index + delta;
  if (next < 0 || next >= rows.length) return;
  if (delta < 0) container.insertBefore(row, rows[next]);
  else container.insertBefore(row, rows[next].nextSibling);
  markUnsaved();
  refreshBulletControls(container);
}

function enableBulletReordering(container) {
  if (container.dataset.reorderReady === '1') return;
  container.dataset.reorderReady = '1';
  container.addEventListener('dragstart', (event) => {
    const handle = event.target.closest('.bullet-drag-handle');
    if (!handle) { event.preventDefault(); return; }
    const row = handle.closest('.bullet-row');
    row.classList.add('dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', 'bullet');
  });
  container.addEventListener('dragend', (event) => {
    const row = event.target.closest('.bullet-row');
    if (row) row.classList.remove('dragging');
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    refreshBulletControls(container);
  });
  container.addEventListener('dragover', (event) => {
    event.preventDefault();
    const dragging = container.querySelector('.bullet-row.dragging');
    const target = event.target.closest('.bullet-row');
    if (!dragging || !target || dragging === target || !container.contains(target)) return;
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    target.classList.add('drag-over');
    const rect = target.getBoundingClientRect();
    const after = event.clientY > rect.top + rect.height / 2;
    if (after) container.insertBefore(dragging, target.nextSibling);
    else container.insertBefore(dragging, target);
  });
  container.addEventListener('drop', (event) => {
    event.preventDefault();
    [...container.children].forEach(c => c.classList.remove('drag-over'));
    markUnsaved();
    refreshBulletControls(container);
  });
}

function addExperience(exp = {}) {
  const node = document.importNode($("experienceTemplate").content, true);
  node.querySelector(".exp-company").value = exp.company || "";
  node.querySelector(".exp-dates").value = exp.dates || "";
  node.querySelector(".exp-role").value = exp.role || "";
  node.querySelector(".exp-location").value = exp.location || "";
  const bullets = node.querySelector(".bullets");
  (exp.bullets || []).forEach(text => {
    const b = document.importNode($("bulletTemplate").content, true);
    b.querySelector(".exp-bullet").value = text;
    bullets.appendChild(b);
  });
  $("experience").appendChild(node);
  enableBulletReordering(bullets);
  refreshBulletControls(bullets);
  refreshCardControls("experience");
}

function addEducation(edu = {}) {
  const node = document.importNode($("educationTemplate").content, true);
  node.querySelector(".edu-institution").value = edu.institution || "";
  node.querySelector(".edu-dates").value = edu.dates || "";
  node.querySelector(".edu-degree").value = edu.degree || "";
  node.querySelector(".edu-location").value = edu.location || "";
  $("education").appendChild(node);
  refreshCardControls("education");
}

function readForm() {
  return {
    section_order: normalizeSectionOrder(resume.section_order),
    personal: {
      name: $("name").value,
      location: $("location").value,
      phone: $("phone").value,
      email: $("email").value,
      linkedin_url: $("linkedin_url").value,
      linkedin_text: $("linkedin_text").value,
    },
    summary: $("summary").value,
    skills: [...document.querySelectorAll("#skills .skill-card")].map(card => ({
      category: card.querySelector(".skill-category").value,
      items: card.querySelector(".skill-items").value,
    })),
    experience: [...document.querySelectorAll("#experience .experience-card")].map(card => ({
      company: card.querySelector(".exp-company").value,
      dates: card.querySelector(".exp-dates").value,
      role: card.querySelector(".exp-role").value,
      location: card.querySelector(".exp-location").value,
      bullets: [...card.querySelectorAll(".exp-bullet")].map(b => b.value),
    })),
    education: [...document.querySelectorAll("#education .education-card")].map(card => ({
      institution: card.querySelector(".edu-institution").value,
      dates: card.querySelector(".edu-dates").value,
      degree: card.querySelector(".edu-degree").value,
      location: card.querySelector(".edu-location").value,
    })),
  };
}

function markUnsaved() {
  $("status").textContent = "Unsaved changes";
}

async function save() {
  resume = readForm();
  const response = await fetch("/api/save", {
    method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(resume)
  });
  const result = await response.json();
  if (!result.ok) throw new Error(result.message || "Save failed");
  $("status").textContent = "Saved locally";
  showToast("Resume saved");
}

async function generate() {
  resume = readForm();
  $("status").textContent = "Generating PDF…";
  $("generateBtn").disabled = true;
  try {
    const response = await fetch("/api/generate", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(resume)
    });
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.message || "PDF generation failed");
    $("status").textContent = "PDF generated";
    $("previewInfo").textContent = "Preview updated just now";
    $("pdfFrame").src = result.pdf_url;
    $("downloadPdf").href = "/download/resume.pdf?ts=" + Date.now();
    showToast("PDF generated successfully");
  } catch (e) {
    $("status").textContent = "Generation failed";
    showToast(e.message);
    alert(e.message);
  } finally {
    $("generateBtn").disabled = false;
  }
}

function renderAll() {
  resume.section_order = normalizeSectionOrder(resume.section_order);
  renderSectionOrder();
  setPersonal();
  $("skills").innerHTML = "";
  $("experience").innerHTML = "";
  $("education").innerHTML = "";
  (resume.skills || []).forEach(addSkill);
  (resume.experience || []).forEach(addExperience);
  (resume.education || []).forEach(addEducation);
  enableCardReordering("skills");
  enableCardReordering("experience");
  enableCardReordering("education");
  refreshCardControls("skills");
  refreshCardControls("experience");
  refreshCardControls("education");
}

async function init() {
  try {
    const response = await fetch("/api/resume", {cache:"no-store"});
    resume = await response.json();
    renderAll();
    $("status").textContent = "Loaded from local file";
    const status = await (await fetch("/api/status", {cache:"no-store"})).json();
    if (status.pdf) {
      $("pdfFrame").src = "/resume.pdf?ts=" + Date.now();
      $("previewInfo").textContent = "Current saved PDF";
    } else if (!status.pdflatex) {
      $("previewInfo").textContent = "pdflatex not found on this machine";
    }
  } catch (e) {
    alert("Could not load the resume data: " + e.message);
  }
}

$("saveBtn").addEventListener("click", () => save().catch(e => alert(e.message)));
$("generateBtn").addEventListener("click", generate);
["name","location","phone","email","linkedin_url","linkedin_text","summary"].forEach(id => {
  $(id).addEventListener("input", markUnsaved);
});
document.addEventListener("input", (event) => {
  if (event.target.matches("#skills input, #experience input, #experience textarea, #education input")) markUnsaved();
});

document.addEventListener("click", (event) => {
  if (event.target.closest(".danger")) markUnsaved();
});

init();
