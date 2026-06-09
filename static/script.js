const BOARD_COORDS = [
  [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0], [9, 0], [10, 0], [11, 0], [12, 0], [13, 0],
  [13, 1], [13, 2], [13, 3], [13, 4], [13, 5], [13, 6],
  [13, 7], [12, 7], [11, 7], [10, 7], [9, 7], [8, 7], [7, 7], [6, 7], [5, 7], [4, 7], [3, 7], [2, 7], [1, 7], [0, 7],
  [0, 6], [0, 5], [0, 4], [0, 3], [0, 2], [0, 1],
];
const BOARD_COLUMNS = 14;
const BOARD_ROWS = 8;

const DRAWER_KEYS = ["players", "ownership", "log", "help"];
const refs = {};

let state = window.gameData;
let selectedFieldId = null;
let activeDrawer = null;
let busy = false;
let toastTimer = null;
let diceTimer = null;
let pollTimer = null;
let lastSignature = "";
let previousPositions = [...(state.positionen || [])];
let eventSearchTerm = "";
let eventTypeFilter = "all";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function eventTime(event) {
  if (!event?.timestamp) {
    return "--:--:--";
  }
  const date = new Date(event.timestamp);
  if (Number.isNaN(date.getTime())) {
    return String(event.timestamp).slice(11, 19) || "--:--:--";
  }
  return date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function getField(fieldId) {
  return state.felder.find((field) => Number(field.feld_id) === Number(fieldId));
}

function getFocusField() {
  if (selectedFieldId) return getField(selectedFieldId);
  if (state.popupFeld) return state.popupFeld;
  if (!state.positionen?.length) return null;
  return state.felder[state.positionen[state.aktiver]];
}

function isPendingField(fieldId) {
  return state.phase === "field_action" && state.popupFeld && Number(state.popupFeld.feld_id) === Number(fieldId);
}

function isSpecialActionField(field) {
  const type = String(field?.typ || "").toLowerCase();
  return ["spezial", "gemeinschaft", "steuer", "los", "gefaengnis", "gefangnis"].includes(type);
}

function isDarkField(field) {
  const color = String(field?.farbe_css || field?.farbe || "").toLowerCase();
  return color.includes("#444") || color.includes("#6d") || color.includes("schwarz") || color.includes("dunkel");
}

function getPhaseLabel() {
  if (state.gameStatus === "finished") return "Beendet";
  if (state.phase === "move") return "Bewegen";
  if (state.phase === "field_action") return "Feldaktion";
  return "Wuerfeln";
}

function getActionCopy() {
  if (state.gameStatus === "finished") {
    return state.lastEvent || "Die Runde ist beendet.";
  }
  if (state.phase === "move" && state.displayRoll) {
    return `${state.activePlayerName} hat ${state.displayRoll[0] + state.displayRoll[1]} gewuerfelt. Jetzt wird gezogen.`;
  }
  if (state.phase === "field_action" && state.popupFeld) {
    return state.popupHint || `${state.activePlayerName} wertet ${state.popupFeld.name} aus.`;
  }
  return `${state.activePlayerName || "Der aktive Spieler"} ist bereit fuer den naechsten Wurf.`;
}

function getInsightCopy(field) {
  if (!field) return "Waehle ein Feld aus, um Details zu sehen.";
  if (state.popupHint && isPendingField(field.feld_id)) return state.popupHint;
  if (field.besitzer) return `${field.name} gehoert ${field.besitzer}.`;
  if (field.ist_kaufbar) return `${field.name} ist frei und kann beim Besuch gesichert werden.`;
  return field.zusatz_regel || "Dieses Feld hat keinen zusaetzlichen Effekt.";
}

function scoreCardMarkup(entry, index) {
  return `
    <article class="score-card${entry.is_active ? " is-active" : ""}">
      <div class="score-topline">
        <span class="player-dot p${index + 1}"></span>
        <strong>${escapeHtml(entry.name)}</strong>
        ${entry.is_active ? '<span class="status-chip status-chip-hot">Am Zug</span>' : ""}
      </div>
      <div class="score-metrics">
        <span>AP <strong>${escapeHtml(entry.drinks)}</strong></span>
        <span>Felder <strong>${escapeHtml(entry.properties)}</strong></span>
        <span>Schritte <strong>${escapeHtml(entry.steps)}</strong></span>
      </div>
      <div class="score-position">${escapeHtml(entry.position)}</div>
    </article>
  `;
}

function ownershipMarkup(entry) {
  const fields = entry.fields.length ? entry.fields.join(", ") : "Noch keine Felder";
  return `
    <article class="ownership-card">
      <strong>${escapeHtml(entry.owner)}</strong>
      <span>${escapeHtml(entry.count)} gesichert</span>
      <p>${escapeHtml(fields)}</p>
    </article>
  `;
}

function eventMarkup(entry) {
  const event = typeof entry === "string"
    ? { message: entry, type: "legacy", severity: "info" }
    : entry;
  return `
    <article class="event-item event-${escapeHtml(event.severity || "info")}">
      <span class="event-time">[${escapeHtml(eventTime(event))}]</span>
      <strong>${escapeHtml(event.type || "info")}</strong>
      <p>${escapeHtml(event.message || "")}</p>
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
  const canAct = state.canAct !== false && state.gameStatus !== "finished";
  if (!isPendingField(field.feld_id)) {
    return '<button type="button" class="secondary-btn" onclick="closeFieldModal()">Schliessen</button>';
  }
  if (!canAct) {
    return `<button type="button" class="primary-btn" disabled>Warten auf ${escapeHtml(state.activePlayerName || "den aktiven Spieler")}</button>`;
  }

  const activePlayerName = state.spieler[state.popupSpieler];
  if (!field.besitzer && field.ist_kaufbar) {
    return `
      <button type="button" class="primary-btn" onclick="handleFieldAction('kaufen', ${field.feld_id})">Feld sichern</button>
      <button type="button" class="secondary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Weiter</button>
    `;
  }
  if (field.besitzer && field.besitzer !== activePlayerName) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('miete', ${field.feld_id})">Abgabe bestaetigen</button>`;
  }
  if (isSpecialActionField(field)) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Effekt ausloesen</button>`;
  }
  return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Zug abschliessen</button>`;
}

function createFieldDetails(field) {
  const owner = field.besitzer || "Noch frei";
  const active = isPendingField(field.feld_id);
  const intro = active ? `${state.activePlayerName} steht aktuell hier.` : "Detailansicht fuer dieses Feld.";
  const note = active && state.popupHint ? state.popupHint : (field.zusatz_regel || "Keine Sonderregel.");
  return `
    <div class="hero-badge">${active ? "Aktive Aktion" : "Feldinfo"}</div>
    <h2>${escapeHtml(field.name)}</h2>
    <p class="modal-intro">${escapeHtml(intro)}</p>
    <div class="modal-meta">
      <div class="modal-row"><span>Typ</span><strong>${escapeHtml(field.typ)}</strong></div>
      <div class="modal-row"><span>Status</span><strong>${escapeHtml(owner)}</strong></div>
      <div class="modal-row"><span>Preis</span><strong>${escapeHtml(field.kaufpreis || "-")}</strong></div>
      <div class="modal-row"><span>Abgabe</span><strong>${escapeHtml(field.miete || "-")}</strong></div>
      <div class="modal-row"><span>Bonus</span><strong>${escapeHtml(field.alkohol_typ || "-")} / ${escapeHtml(field.alkohol_menge || "-")}</strong></div>
    </div>
    <div class="modal-note">${escapeHtml(note)}</div>
    <div class="modal-actions">${buildFieldActions(field)}</div>
  `;
}

function renderBoardGrid() {
  const coordToField = new Map(BOARD_COORDS.map((coord, index) => [coord.join(","), index]));
  const tiles = [];

  for (let y = 0; y < BOARD_ROWS; y += 1) {
    for (let x = 0; x < BOARD_COLUMNS; x += 1) {
      const fieldIndex = coordToField.get(`${x},${y}`);
      if (fieldIndex === undefined) {
        tiles.push('<div class="board-center-gap" aria-hidden="true"></div>');
        continue;
      }

      const field = state.felder[fieldIndex];
      const tokens = state.positionen.map((position, index) => {
        if (position !== fieldIndex) return "";
        const moved = previousPositions[index] !== undefined && previousPositions[index] !== position ? " just-moved" : "";
        const active = index === state.aktiver ? " active-token" : "";
        return `<span class="player-token p${index + 1}${moved}${active}" title="${escapeHtml(state.spieler[index])}">${index + 1}</span>`;
      }).join("");
      const current = state.positionen[state.aktiver] === fieldIndex ? " is-current" : "";
      const pending = isPendingField(field.feld_id) ? " pending-action" : "";
      const dark = isDarkField(field) ? " is-dark-field" : "";
      const selected = Number(selectedFieldId) === Number(field.feld_id) ? " is-selected" : "";
      const title = `${fieldIndex + 1}. ${field.name} (${field.typ})`;

      tiles.push(`
        <button
          type="button"
          class="field-tile${field.ist_kaufbar ? " field-buyable" : ""}${current}${pending}${dark}${selected}"
          style="--field-color: ${escapeHtml(field.farbe_css)};"
          onclick="showFieldInfo(${field.feld_id})"
          aria-label="${escapeHtml(title)}"
          title="${escapeHtml(title)}"
        >
          <span class="field-index">${fieldIndex + 1}</span>
          <span class="field-name">${escapeHtml(field.name)}</span>
          <span class="field-type">${escapeHtml(field.typ)}</span>
          <span class="field-owner">${escapeHtml(field.besitzer || field.kaufpreis || "")}</span>
          <span class="field-players">${tokens}</span>
        </button>
      `);
    }
  }
  refs.boardGrid.innerHTML = tiles.join("");
  previousPositions = [...(state.positionen || [])];
}

function renderScoreboard() {
  refs.playerCountChip.textContent = `${state.spieler.length} aktiv`;
  refs.scoreList.innerHTML = state.scoreboard.map(scoreCardMarkup).join("");
}

function renderOwnership() {
  refs.ownershipCountChip.textContent = `${state.ownership.length} aktiv`;
  refs.ownershipList.innerHTML = state.ownership.length
    ? state.ownership.map(ownershipMarkup).join("")
    : '<p class="empty-note">Noch wurde kein Feld gesichert.</p>';
}

function renderEventLog() {
  const entries = (state.eventLog || []).filter((entry) => {
    const event = typeof entry === "string" ? { message: entry, type: "legacy" } : entry;
    const matchesType = eventTypeFilter === "all" || event.type === eventTypeFilter || event.severity === eventTypeFilter;
    const haystack = `${event.type || ""} ${event.severity || ""} ${event.message || ""}`.toLowerCase();
    return matchesType && haystack.includes(eventSearchTerm);
  });

  refs.eventLog.innerHTML = entries.length
    ? entries.map(eventMarkup).join("")
    : '<p class="empty-note">Der Spielverlauf erscheint hier nach dem Start.</p>';
  window.requestAnimationFrame(() => {
    refs.eventLog.scrollTop = refs.eventLog.scrollHeight;
  });
}

function renderQuickStats() {
  const highlights = state.highlights || {};
  refs.quickStats.innerHTML = [
    statCardMarkup("Runde", `#${highlights.runde || 1}`, "Aktuell"),
    statCardMarkup("Zug", `#${highlights.zugnummer || 1}`, "Gesamt"),
    statCardMarkup("Spitze", highlights.leaderName || "Offen", highlights.leaderName ? `${highlights.leaderCount} Felder` : "Keine Fuehrung"),
    statCardMarkup("Frei", `${highlights.freieFelder ?? 0}`, "Felder"),
  ].join("");
}

function renderBoardInsights() {
  const field = getFocusField();
  refs.boardInsights.innerHTML = `
    <article class="insight-card">
      <span class="insight-label">Fokus</span>
      <strong>${escapeHtml(field ? field.name : "Bereit")}</strong>
      <p>${escapeHtml(getInsightCopy(field))}</p>
    </article>
    <article class="insight-card">
      <span class="insight-label">Status</span>
      <strong>${escapeHtml(getPhaseLabel())}</strong>
      <p>${escapeHtml(getActionCopy())}</p>
      <div class="legend-row">
        <span class="legend-pill"><span class="legend-dot legend-dot-active"></span>Aktiv</span>
        <span class="legend-pill"><span class="legend-dot legend-dot-pending"></span>Offen</span>
      </div>
    </article>
  `;
}

function renderActionPanel() {
  const canAct = state.canAct !== false && state.gameStatus !== "finished";
  const title = state.activePlayerName || "Bereit";
  let actions = `<button type="button" class="primary-btn" onclick="handleRoll()" ${busy || !canAct ? "disabled" : ""}>${canAct ? "Wuerfeln" : "Warten"}</button>`;

  if (state.gameStatus === "finished") {
    actions = '<button type="button" class="primary-btn" disabled>Runde beendet</button>';
  } else if (state.phase === "move") {
    actions = `<button type="button" class="primary-btn" onclick="handleMove()" ${busy || !canAct ? "disabled" : ""}>${canAct ? "Figur bewegen" : "Warten"}</button>`;
  } else if (state.phase === "field_action" && state.popupFeld) {
    actions = `<button type="button" class="primary-btn" onclick="showPendingField()" ${busy ? "disabled" : ""}>Feld oeffnen</button>`;
  }

  refs.phaseChip.textContent = getPhaseLabel();
  refs.centerPlayerName.textContent = title;
  refs.currentFieldButton.disabled = state.phase !== "field_action" || busy;
  refs.turnSummary.innerHTML = `
    <div class="turn-summary-hero">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(getActionCopy())}</span>
    </div>
  `;
  refs.commandActions.innerHTML = actions;
}

function renderCenterCard() {
  refs.centerTitle.textContent = state.phase === "field_action" && state.popupFeld ? state.popupFeld.name : (state.activePlayerName || "Bereit");
  refs.centerCopy.textContent = getActionCopy();
  refs.rollStatus.textContent = state.lastEvent || "";

  const roll = state.displayRoll || [1, 1];
  refs.w1.src = `/static/dice/${roll[0]}.png`;
  refs.w2.src = `/static/dice/${roll[1]}.png`;
}

function renderModal() {
  if (!selectedFieldId) {
    refs.modal.classList.remove("open");
    refs.modal.setAttribute("aria-hidden", "true");
    return;
  }
  const field = getField(selectedFieldId);
  if (!field) {
    selectedFieldId = null;
    renderModal();
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

  if (options.closeModal) selectedFieldId = null;
  if (options.openPending && nextState.popupFeld) selectedFieldId = nextState.popupFeld.feld_id;
  if (selectedFieldId && !getField(selectedFieldId)) selectedFieldId = null;

  renderApp();
  if (options.toast) showToast(options.toast);
}

function setBusy(nextBusy) {
  busy = nextBusy;
  renderActionPanel();
}

function showToast(message) {
  if (!message) return;
  refs.toast.textContent = message;
  refs.toast.classList.add("show");
  window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => refs.toast.classList.remove("show"), 2400);
}

async function postJson(url, payload = null) {
  const options = { method: "POST", headers: { "Content-Type": "application/json" } };
  if (payload) options.body = JSON.stringify(payload);
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || !data.ok) {
    const error = new Error(data.msg || "Aktion konnte nicht ausgefuehrt werden.");
    error.state = data.state;
    throw error;
  }
  return data;
}

function getStateSignature(nextState) {
  return JSON.stringify({
    phase: nextState.phase,
    status: nextState.gameStatus,
    active: nextState.aktiver,
    positions: nextState.positionen,
    points: nextState.konto,
    totals: nextState.gesamt,
    roll: nextState.displayRoll,
    popup: nextState.popupFeld ? nextState.popupFeld.feld_id : null,
    last: nextState.lastEvent,
    logSize: nextState.eventLog?.length || 0,
    ownership: nextState.ownership,
    canAct: nextState.canAct,
  });
}

async function refreshState({ silent = true } = {}) {
  if (busy) return;
  try {
    const response = await fetch("/api/state");
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.msg || "Spielstand konnte nicht aktualisiert werden.");
    const signature = getStateSignature(data.state);
    if (signature !== lastSignature) {
      const previousPhase = state.phase;
      const previousRoll = state.displayRoll;
      setState(data.state);
      lastSignature = signature;
      if (data.state.phase === "move" && previousPhase !== "move" && data.state.displayRoll && JSON.stringify(previousRoll) !== JSON.stringify(data.state.displayRoll)) {
        animateDice(data.state.displayRoll);
      }
    }
  } catch (error) {
    if (!silent) showToast(error.message);
  }
}

function animateDice(roll) {
  if (!roll) return;
  window.clearInterval(diceTimer);
  let ticks = 0;
  refs.diceDisplay.classList.add("rolling");
  refs.rollStatus.textContent = `${state.activePlayerName} wuerfelt ...`;

  diceTimer = window.setInterval(() => {
    refs.w1.src = `/static/dice/${Math.floor(Math.random() * 6) + 1}.png`;
    refs.w2.src = `/static/dice/${Math.floor(Math.random() * 6) + 1}.png`;
    ticks += 1;
    if (ticks >= 11) {
      window.clearInterval(diceTimer);
      refs.w1.src = `/static/dice/${roll[0]}.png`;
      refs.w2.src = `/static/dice/${roll[1]}.png`;
      refs.diceDisplay.classList.remove("rolling");
      refs.rollStatus.textContent = `${state.activePlayerName} hat ${roll[0] + roll[1]} gewuerfelt.`;
    }
  }, 65);
}

function openDrawer(key) {
  closeDrawer();
  const drawer = refs.drawers[key];
  if (!drawer) return;
  drawer.classList.add("open");
  drawer.setAttribute("aria-hidden", "false");
  refs.drawerScrim.classList.add("open");
  refs.drawerScrim.setAttribute("aria-hidden", "false");
  activeDrawer = key;
}

function closeDrawer(key = null) {
  if (key && activeDrawer !== key) {
    refs.drawers[key]?.classList.remove("open");
    refs.drawers[key]?.setAttribute("aria-hidden", "true");
    return;
  }
  DRAWER_KEYS.forEach((drawerKey) => {
    refs.drawers[drawerKey].classList.remove("open");
    refs.drawers[drawerKey].setAttribute("aria-hidden", "true");
  });
  refs.drawerScrim.classList.remove("open");
  refs.drawerScrim.setAttribute("aria-hidden", "true");
  activeDrawer = null;
}

function toggleDrawer(key) {
  activeDrawer === key ? closeDrawer() : openDrawer(key);
}

function closeFieldModal() {
  selectedFieldId = null;
  renderModal();
  renderBoardGrid();
  renderBoardInsights();
}

function showFieldInfo(fieldId) {
  selectedFieldId = fieldId;
  renderModal();
  renderBoardGrid();
  renderBoardInsights();
}

function showPendingField() {
  if (!state.popupFeld) return;
  selectedFieldId = state.popupFeld.feld_id;
  renderModal();
  renderBoardGrid();
  renderBoardInsights();
}

async function handleRoll() {
  if (busy) return;
  setBusy(true);
  try {
    const data = await postJson("/zug_wuerfeln");
    setState(data.state, { toast: data.state.lastEvent });
    lastSignature = getStateSignature(data.state);
    animateDice(data.state.displayRoll);
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function handleMove() {
  if (busy) return;
  setBusy(true);
  try {
    const data = await postJson("/zug_ziehen");
    setState(data.state, { openPending: true, toast: data.state.lastEvent });
    lastSignature = getStateSignature(data.state);
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function handleFieldAction(action, fieldId) {
  if (busy) return;
  setBusy(true);
  try {
    const data = await postJson("/feld_aktion", { aktion: action, feld: fieldId });
    setState(data.state, { closeModal: true, toast: data.state.lastEvent });
    lastSignature = getStateSignature(data.state);
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
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
  refs.eventSearch = document.getElementById("eventSearch");
  refs.eventFilter = document.getElementById("eventFilter");
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
  refs.diceDisplay = document.getElementById("diceDisplay");
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
    if (event.target === refs.modal) closeFieldModal();
  });
  refs.drawerScrim.addEventListener("click", () => closeDrawer());
  refs.eventSearch.addEventListener("input", (event) => {
    eventSearchTerm = event.target.value.trim().toLowerCase();
    renderEventLog();
  });
  refs.eventFilter.addEventListener("change", (event) => {
    eventTypeFilter = event.target.value;
    renderEventLog();
  });
  DRAWER_KEYS.forEach((key) => refs.drawerButtons[key].addEventListener("click", () => toggleDrawer(key)));
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
  lastSignature = getStateSignature(state);
  pollTimer = window.setInterval(() => refreshState(), 1000);
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
