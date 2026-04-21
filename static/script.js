const BOARD_COORDS = [
  [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0], [9, 0], [10, 0],
  [10, 1], [10, 2], [10, 3], [10, 4], [10, 5], [10, 6], [10, 7], [10, 8], [10, 9], [10, 10],
  [9, 10], [8, 10], [7, 10], [6, 10], [5, 10], [4, 10], [3, 10], [2, 10], [1, 10], [0, 10],
  [0, 9], [0, 8], [0, 7], [0, 6], [0, 5], [0, 4], [0, 3], [0, 2], [0, 1],
];

const refs = {};
const DRAWER_KEYS = ["players", "ownership", "log", "help"];

let state = window.gameData;
let selectedFieldId = null;
let activeDrawer = null;
let busy = false;
let toastTimer = null;
let animationTimer = null;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function getField(fieldId) {
  return state.felder.find((field) => Number(field.feld_id) === Number(fieldId));
}

function getFocusField() {
  if (selectedFieldId) {
    return getField(selectedFieldId);
  }
  if (state.popupFeld) {
    return state.popupFeld;
  }
  if (!state.positionen?.length) {
    return null;
  }
  return state.felder[state.positionen[state.aktiver]];
}

function isPendingField(fieldId) {
  return state.phase === "field_action"
    && state.popupFeld
    && Number(state.popupFeld.feld_id) === Number(fieldId);
}

function isSpecialActionField(field) {
  if (!field) {
    return false;
  }
  const type = String(field.typ || "").toLowerCase();
  return ["spezial", "gemeinschaft", "steuer", "los", "gefängnis", "gefaengnis"].includes(type);
}

function getPhaseChipText() {
  if (state.phase === "move") {
    return "Bewegen";
  }
  if (state.phase === "field_action") {
    return "Feldaktion";
  }
  return "Würfeln";
}

function getCenterCardCopy() {
  if (state.phase === "move" && state.displayRoll) {
    return `${state.activePlayerName} hat ${state.displayRoll[0] + state.displayRoll[1]} gewürfelt und zieht jetzt weiter.`;
  }
  if (state.phase === "field_action" && state.popupFeld) {
    return state.popupHint || `${state.activePlayerName} wertet jetzt ${state.popupFeld.name} aus.`;
  }
  return "Die Runde wartet auf den nächsten Wurf.";
}

function getInsightCopy(field) {
  if (!field) {
    return "Wähle ein Feld auf dem Spielbrett aus, um zusätzliche Informationen zu sehen.";
  }
  if (state.popupHint && isPendingField(field.feld_id)) {
    return state.popupHint;
  }
  if (field.besitzer) {
    return `${field.name} gehört aktuell ${field.besitzer}. Ein Besuch auf diesem Feld löst die passende Abgabe aus.`;
  }
  if (field.ist_kaufbar) {
    return `${field.name} ist frei und kann beim nächsten Besuch gesichert werden.`;
  }
  return field.zusatz_regel || "Dieses Feld bringt Abwechslung in die Partie.";
}

function scoreCardMarkup(entry, index) {
  const activeBadge = entry.is_active ? '<span class="status-chip">Am Zug</span>' : "";
  return `
    <article class="score-card${entry.is_active ? " is-active" : ""}">
      <div class="score-topline">
        <span class="player-dot p${index + 1}"></span>
        <strong>${escapeHtml(entry.name)}</strong>
        ${activeBadge}
      </div>
      <div class="score-metrics">
        <span>Aktionspunkte: ${escapeHtml(entry.drinks)}</span>
        <span>Schritte: ${escapeHtml(entry.steps)}</span>
        <span>Gesicherte Felder: ${escapeHtml(entry.properties)}</span>
      </div>
      <div class="score-position">Aktuelle Position: ${escapeHtml(entry.position)}</div>
    </article>
  `;
}

function ownershipMarkup(entry) {
  const fields = entry.fields.length ? escapeHtml(entry.fields.join(", ")) : "Noch keine Felder";
  return `
    <article class="ownership-card">
      <strong>${escapeHtml(entry.owner)}</strong>
      <div class="ownership-meta">
        <span>${escapeHtml(entry.count)} Feld${entry.count === 1 ? "" : "er"} gesichert</span>
        <span>${fields}</span>
      </div>
    </article>
  `;
}

function eventMarkup(message, index) {
  const label = index === 0 ? "Neu" : `Eintrag ${index + 1}`;
  return `
    <article class="event-item">
      <strong>${label}</strong>
      <p>${escapeHtml(message)}</p>
    </article>
  `;
}

function statCardMarkup(label, value, meta) {
  return `
    <article class="stat-card">
      <span class="stat-label">${escapeHtml(label)}</span>
      <strong class="stat-value">${escapeHtml(value)}</strong>
      <span class="stat-meta">${escapeHtml(meta)}</span>
    </article>
  `;
}

function buildFieldActions(field) {
  if (!isPendingField(field.feld_id)) {
    return '<button type="button" class="secondary-btn" onclick="closeFieldModal()">Schließen</button>';
  }

  const activePlayerName = state.spieler[state.popupSpieler];

  if (!field.besitzer && field.ist_kaufbar) {
    return `
      <button type="button" class="primary-btn" onclick="handleFieldAction('kaufen', ${field.feld_id})">Feld sichern</button>
      <button type="button" class="secondary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Ohne Kauf weiter</button>
    `;
  }

  if (field.besitzer && field.besitzer !== activePlayerName) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('miete', ${field.feld_id})">Abgabe bestätigen</button>`;
  }

  if (isSpecialActionField(field)) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Effekt auslösen</button>`;
  }

  return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Zug abschließen</button>`;
}

function createFieldDetails(field) {
  const owner = field.besitzer ? field.besitzer : "Noch frei";
  const intro = isPendingField(field.feld_id)
    ? `${escapeHtml(state.activePlayerName)} befindet sich aktuell auf diesem Feld.`
    : "Detailansicht für dieses Spielfeld.";
  const note = isPendingField(field.feld_id) && state.popupHint
    ? state.popupHint
    : (field.zusatz_regel || "Dieses Feld besitzt keine zusätzliche Sonderregel.");

  return `
    <div class="hero-badge">${isPendingField(field.feld_id) ? "Aktive Feldaktion" : "Spielfeld-Info"}</div>
    <h2>${escapeHtml(field.name)}</h2>
    <p class="modal-intro">${escapeHtml(intro)}</p>
    <div class="modal-meta">
      <div class="modal-row"><span>Kategorie</span><strong>${escapeHtml(field.typ)}</strong></div>
      <div class="modal-row"><span>Status</span><strong>${escapeHtml(owner)}</strong></div>
      <div class="modal-row"><span>Preis</span><strong>${escapeHtml(field.kaufpreis || "—")}</strong></div>
      <div class="modal-row"><span>Abgabe</span><strong>${escapeHtml(field.miete || "—")}</strong></div>
      <div class="modal-row"><span>Bonus</span><strong>${escapeHtml(field.alkohol_typ)} · ${escapeHtml(field.alkohol_menge)}</strong></div>
    </div>
    <div class="modal-note">${escapeHtml(note)}</div>
    <div class="modal-actions">${buildFieldActions(field)}</div>
  `;
}

function renderBoardGrid() {
  const coordToField = new Map(BOARD_COORDS.map((coord, index) => [coord.join(","), index]));
  const html = [];

  for (let y = 0; y < 11; y += 1) {
    for (let x = 0; x < 11; x += 1) {
      const key = `${x},${y}`;
      if (!coordToField.has(key)) {
        html.push('<div class="board-center-gap"></div>');
        continue;
      }

      const fieldIndex = coordToField.get(key);
      const field = state.felder[fieldIndex];
      const tokens = state.positionen
        .map((position, index) => (position === fieldIndex
          ? `<span class="player-token p${index + 1}">${index + 1}</span>`
          : ""))
        .join("");

      const activeClass = state.positionen[state.aktiver] === fieldIndex ? " is-current" : "";
      const pendingClass = isPendingField(field.feld_id) ? " pending-action" : "";
      const owner = field.besitzer ? `<span class="field-owner">${escapeHtml(field.besitzer)}</span>` : "";
      const price = field.kaufpreis ? `<span class="field-price">${escapeHtml(field.kaufpreis)}</span>` : "";

      html.push(`
        <button
          type="button"
          class="field-tile${field.ist_kaufbar ? " field-buyable" : ""}${activeClass}${pendingClass}"
          style="background: ${escapeHtml(field.farbe_css)};"
          onclick="showFieldInfo(${field.feld_id})"
        >
          <div>
            <span class="field-name">${escapeHtml(field.name)}</span>
            <span class="field-type">${escapeHtml(field.typ)}</span>
            ${owner}
          </div>
          <div>
            ${price}
            <div class="field-players">${tokens}</div>
          </div>
        </button>
      `);
    }
  }

  refs.boardGrid.innerHTML = html.join("");
}

function renderScoreboard() {
  refs.playerCountChip.textContent = `${state.spieler.length} aktiv`;
  refs.scoreList.innerHTML = state.scoreboard.map(scoreCardMarkup).join("");
}

function renderOwnership() {
  refs.ownershipCountChip.textContent = `${state.ownership.length} aktiv`;
  if (!state.ownership.length) {
    refs.ownershipList.innerHTML = '<p class="empty-note">Noch wurde kein Feld dauerhaft gesichert.</p>';
    return;
  }

  refs.ownershipList.innerHTML = state.ownership.map(ownershipMarkup).join("");
}

function renderEventLog() {
  const entries = state.eventLog && state.eventLog.length
    ? state.eventLog.map(eventMarkup).join("")
    : '<p class="empty-note">Der Spielverlauf erscheint hier, sobald die Runde startet.</p>';
  refs.eventLog.innerHTML = entries;
}

function renderQuickStats() {
  const highlights = state.highlights || {};
  const leaderName = highlights.leaderName || "Offen";
  const leaderMeta = highlights.leaderName
    ? `${highlights.leaderCount} Feld${highlights.leaderCount === 1 ? "" : "er"} vorne`
    : "Noch kein Vorsprung";

  refs.quickStats.innerHTML = [
    statCardMarkup("Runde", `#${highlights.runde || 1}`, "Aktuell"),
    statCardMarkup("Zug", `#${highlights.zugnummer || 1}`, "Gesamt"),
    statCardMarkup("Spitze", leaderName, leaderMeta),
    statCardMarkup("Frei", `${highlights.freieFelder ?? 0}`, "Noch offen"),
  ].join("");
}

function renderBoardInsights() {
  const focusField = getFocusField();
  const nextAction = state.phase === "field_action"
    ? "Feldaktion abschließen"
    : state.phase === "move"
      ? "Figur weiterziehen"
      : "Würfeln";

  refs.boardInsights.innerHTML = `
    <article class="insight-card">
      <span class="insight-label">Fokusfeld</span>
      <strong>${escapeHtml(focusField ? focusField.name : "Bereit für den Start")}</strong>
      <p>${escapeHtml(getInsightCopy(focusField))}</p>
    </article>
    <article class="insight-card">
      <span class="insight-label">Nächster Schritt</span>
      <strong>${escapeHtml(nextAction)}</strong>
      <p>Weiße Umrandung zeigt die aktuelle Position. Gold markiert ein Feld, das noch ausgewertet werden muss.</p>
      <div class="legend-row">
        <span class="legend-pill"><span class="legend-dot legend-dot-active"></span>Aktive Position</span>
        <span class="legend-pill"><span class="legend-dot legend-dot-pending"></span>Offene Aktion</span>
      </div>
    </article>
  `;
}

function renderActionPanel() {
  const total = state.displayRoll ? state.displayRoll[0] + state.displayRoll[1] : null;
  const title = state.activePlayerName || "Bereit";
  let body = "Der nächste Zug kann gestartet werden.";
  let actions = `
    <button type="button" class="primary-btn" onclick="handleRoll()" ${busy ? "disabled" : ""}>Würfeln</button>
  `;

  if (state.phase === "move" && total !== null) {
    body = `${title} hat ${total} gewürfelt. Jetzt die Figur bewegen.`;
    actions = `
      <button type="button" class="primary-btn" onclick="handleMove()" ${busy ? "disabled" : ""}>Figur bewegen</button>
    `;
  } else if (state.phase === "field_action" && state.popupFeld) {
    body = state.popupHint || `${title} ist auf ${state.popupFeld.name} gelandet.`;
    actions = `
      <button type="button" class="primary-btn" onclick="showPendingField()" ${busy ? "disabled" : ""}>Feld öffnen</button>
    `;
  }

  refs.phaseChip.textContent = getPhaseChipText();
  refs.turnSummary.innerHTML = `
    <div class="turn-summary-hero">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(body)}</span>
    </div>
  `;
  refs.centerPlayerName.textContent = title;
  refs.currentFieldButton.disabled = state.phase !== "field_action" || busy;
  refs.commandActions.innerHTML = actions;
}

function renderCenterCard() {
  refs.centerTitle.textContent = state.phase === "field_action" && state.popupFeld
    ? state.popupFeld.name
    : (state.activePlayerName || "Bereit");
  refs.centerCopy.textContent = getCenterCardCopy();
  refs.rollStatus.textContent = state.lastEvent || "";

  const displayRoll = state.displayRoll || [1, 1];
  refs.w1.src = `/static/dice/${displayRoll[0]}.png`;
  refs.w2.src = `/static/dice/${displayRoll[1]}.png`;
}

function renderModal() {
  if (!selectedFieldId) {
    refs.modal.classList.remove("open");
    refs.modal.setAttribute("aria-hidden", "true");
    return;
  }

  const field = getField(selectedFieldId);
  if (!field) {
    closeFieldModal();
    return;
  }

  refs.modalContent.innerHTML = createFieldDetails(field);
  refs.modal.classList.add("open");
  refs.modal.setAttribute("aria-hidden", "false");
}

function renderApp() {
  renderBoardGrid();
  renderScoreboard();
  renderOwnership();
  renderEventLog();
  renderQuickStats();
  renderActionPanel();
  renderCenterCard();
  renderBoardInsights();
  renderModal();
}

function setState(nextState, options = {}) {
  state = nextState;
  window.gameData = nextState;

  if (options.closeModal) {
    selectedFieldId = null;
  }

  if (options.openPending && nextState.popupFeld) {
    selectedFieldId = nextState.popupFeld.feld_id;
  } else if (selectedFieldId && !getField(selectedFieldId)) {
    selectedFieldId = null;
  }

  renderApp();

  if (options.toast) {
    showToast(options.toast);
  }
}

function setBusy(nextBusy) {
  busy = nextBusy;
  renderActionPanel();
}

function showToast(message) {
  if (!message) {
    return;
  }

  refs.toast.textContent = message;
  refs.toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => refs.toast.classList.remove("show"), 2200);
}

async function postJson(url, payload = null) {
  const options = {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  };

  if (payload) {
    options.body = JSON.stringify(payload);
  }

  const response = await fetch(url, options);
  const data = await response.json();

  if (!response.ok || !data.ok) {
    throw new Error(data.msg || "Aktion konnte nicht ausgeführt werden.");
  }

  return data;
}

function animateDice(roll) {
  if (!roll) {
    return;
  }

  window.clearInterval(animationTimer);
  let count = 0;
  const maxCount = 10;

  refs.rollStatus.textContent = `${state.activePlayerName} würfelt ...`;

  animationTimer = window.setInterval(() => {
    const randomOne = Math.floor(Math.random() * 6) + 1;
    const randomTwo = Math.floor(Math.random() * 6) + 1;
    refs.w1.src = `/static/dice/${randomOne}.png`;
    refs.w2.src = `/static/dice/${randomTwo}.png`;
    count += 1;

    if (count >= maxCount) {
      window.clearInterval(animationTimer);
      refs.w1.src = `/static/dice/${roll[0]}.png`;
      refs.w2.src = `/static/dice/${roll[1]}.png`;
      refs.rollStatus.textContent = `${state.activePlayerName} hat ${roll[0] + roll[1]} gewürfelt.`;
    }
  }, 75);
}

function openDrawer(key) {
  closeDrawer();
  const drawer = refs.drawers[key];
  if (!drawer) {
    return;
  }

  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  refs.drawerScrim.classList.add("open");
  refs.drawerScrim.setAttribute("aria-hidden", "false");
  activeDrawer = key;
}

function closeDrawer(key = null) {
  if (key && activeDrawer !== key) {
    const drawer = refs.drawers[key];
    if (drawer) {
      drawer.classList.remove("open");
      drawer.setAttribute("aria-hidden", "true");
    }
    return;
  }

  DRAWER_KEYS.forEach((drawerKey) => {
    const drawer = refs.drawers[drawerKey];
    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
  });
  refs.drawerScrim.classList.remove("open");
  refs.drawerScrim.setAttribute("aria-hidden", "true");
  activeDrawer = null;
}

function toggleDrawer(key) {
  if (activeDrawer === key) {
    closeDrawer();
    return;
  }
  openDrawer(key);
}

function closeFieldModal() {
  selectedFieldId = null;
  renderModal();
  renderBoardInsights();
}

function showFieldInfo(fieldId) {
  selectedFieldId = fieldId;
  renderModal();
  renderBoardInsights();
}

function showPendingField() {
  if (!state.popupFeld) {
    return;
  }

  selectedFieldId = state.popupFeld.feld_id;
  renderModal();
  renderBoardInsights();
}

async function handleRoll() {
  if (busy) {
    return;
  }

  setBusy(true);
  try {
    const data = await postJson("/zug_wuerfeln");
    setState(data.state, { toast: data.state.lastEvent });
    animateDice(data.state.displayRoll);
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function handleMove() {
  if (busy) {
    return;
  }

  setBusy(true);
  try {
    const data = await postJson("/zug_ziehen");
    setState(data.state, {
      openPending: true,
      toast: data.state.lastEvent,
    });
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function handleFieldAction(action, fieldId) {
  if (busy) {
    return;
  }

  setBusy(true);
  try {
    const data = await postJson("/feld_aktion", { aktion: action, feld: fieldId });
    setState(data.state, {
      closeModal: true,
      toast: data.state.lastEvent,
    });
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

function cacheRefs() {
  refs.modal = document.getElementById("fieldModal");
  refs.modalContent = document.getElementById("fieldModalContent");
  refs.boardGrid = document.getElementById("boardGrid");
  refs.scoreList = document.getElementById("scoreList");
  refs.ownershipList = document.getElementById("ownershipList");
  refs.eventLog = document.getElementById("eventLog");
  refs.commandActions = document.getElementById("commandActions");
  refs.phaseChip = document.getElementById("phaseChip");
  refs.turnSummary = document.getElementById("turnSummary");
  refs.quickStats = document.getElementById("quickStats");
  refs.currentFieldButton = document.getElementById("currentFieldButton");
  refs.playerCountChip = document.getElementById("playerCountChip");
  refs.ownershipCountChip = document.getElementById("ownershipCountChip");
  refs.centerTitle = document.getElementById("centerTitle");
  refs.centerPlayerName = document.getElementById("centerPlayerName");
  refs.centerCopy = document.getElementById("centerCopy");
  refs.rollStatus = document.getElementById("rollStatus");
  refs.boardInsights = document.getElementById("boardInsights");
  refs.toast = document.getElementById("toast");
  refs.w1 = document.getElementById("w1");
  refs.w2 = document.getElementById("w2");
  refs.drawerScrim = document.getElementById("drawerScrim");
  refs.drawers = {
    players: document.getElementById("playersPanel"),
    ownership: document.getElementById("ownershipPanel"),
    log: document.getElementById("logPanel"),
    help: document.getElementById("helpPanel"),
  };
  refs.drawerButtons = {
    players: document.getElementById("playersPanelButton"),
    ownership: document.getElementById("ownershipPanelButton"),
    log: document.getElementById("logPanelButton"),
    help: document.getElementById("helpPanelButton"),
  };
}

function bindEvents() {
  refs.currentFieldButton.addEventListener("click", showPendingField);
  refs.modal.addEventListener("click", (event) => {
    if (event.target === refs.modal) {
      closeFieldModal();
    }
  });
  refs.drawerScrim.addEventListener("click", () => closeDrawer());
  DRAWER_KEYS.forEach((key) => {
    refs.drawerButtons[key].addEventListener("click", () => toggleDrawer(key));
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeFieldModal();
      closeDrawer();
    }
  });
}

function bootBoard() {
  cacheRefs();
  bindEvents();
  renderApp();

  if (state.phase === "field_action" && state.popupFeld) {
    selectedFieldId = state.popupFeld.feld_id;
    renderModal();
  } else if (state.phase === "move" && state.displayRoll) {
    animateDice(state.displayRoll);
  }
}

document.addEventListener("DOMContentLoaded", bootBoard);

window.closeDrawer = closeDrawer;
window.closeFieldModal = closeFieldModal;
window.showFieldInfo = showFieldInfo;
window.showPendingField = showPendingField;
window.handleFieldAction = handleFieldAction;
window.handleRoll = handleRoll;
window.handleMove = handleMove;
