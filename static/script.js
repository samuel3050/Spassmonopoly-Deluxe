const BOARD_COORDS = [
  [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0], [9, 0], [10, 0],
  [10, 1], [10, 2], [10, 3], [10, 4], [10, 5], [10, 6], [10, 7], [10, 8], [10, 9], [10, 10],
  [9, 10], [8, 10], [7, 10], [6, 10], [5, 10], [4, 10], [3, 10], [2, 10], [1, 10], [0, 10],
  [0, 9], [0, 8], [0, 7], [0, 6], [0, 5], [0, 4], [0, 3], [0, 2], [0, 1],
];

const refs = {};
let state = window.gameData;
let selectedFieldId = null;
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

function isPendingField(fieldId) {
  return state.phase === "field_action"
    && state.popupFeld
    && Number(state.popupFeld.feld_id) === Number(fieldId);
}

function getPhaseChipText() {
  if (state.phase === "move") {
    return "Wurf bestaetigen";
  }
  if (state.phase === "field_action") {
    return "Feldaktion";
  }
  return "Bereit";
}

function getCenterCardCopy() {
  if (state.phase === "move" && state.displayRoll) {
    return `${state.activePlayerName} hat ${state.displayRoll[0] + state.displayRoll[1]} gewuerfelt.`;
  }
  if (state.phase === "field_action" && state.popupFeld) {
    return `${state.activePlayerName} ist auf ${state.popupFeld.name} gelandet.`;
  }
  return "Alles Wichtige bleibt im sichtbaren Bereich.";
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
        <span>Feld: ${escapeHtml(entry.position)}</span>
        <span>Schlucke: ${escapeHtml(entry.drinks)}</span>
        <span>Zuege: ${escapeHtml(entry.steps)}</span>
        <span>Besitz: ${escapeHtml(entry.properties)}</span>
      </div>
    </article>
  `;
}

function ownershipMarkup(entry) {
  const fields = entry.fields.length ? escapeHtml(entry.fields.join(", ")) : "Keine Felder";
  return `
    <article class="ownership-card">
      <strong>${escapeHtml(entry.owner)}</strong>
      <div class="ownership-meta">
        <span>${escapeHtml(entry.count)} Feld${entry.count === 1 ? "" : "er"}</span>
        <span>${fields}</span>
      </div>
    </article>
  `;
}

function eventMarkup(message, index) {
  const label = index === 0 ? "Zuletzt" : `Eintrag ${index + 1}`;
  return `
    <article class="event-item">
      <strong>${label}</strong>
      <p>${escapeHtml(message)}</p>
    </article>
  `;
}

function buildFieldActions(field) {
  if (!isPendingField(field.feld_id)) {
    return '<button type="button" class="secondary-btn" onclick="closeFieldModal()">Schliessen</button>';
  }

  const activePlayerName = state.spieler[state.popupSpieler];

  if (!field.besitzer && field.ist_kaufbar) {
    return `
      <button type="button" class="primary-btn" onclick="handleFieldAction('kaufen', ${field.feld_id})">Kaufen</button>
      <button type="button" class="secondary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Nicht kaufen</button>
    `;
  }

  if (field.besitzer && field.besitzer !== activePlayerName) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('miete', ${field.feld_id})">Miete zahlen</button>`;
  }

  return '<button type="button" class="secondary-btn" onclick="handleFieldAction(\'skip\', ' + field.feld_id + ')">Weiter</button>';
}

function createFieldDetails(field) {
  const owner = field.besitzer ? field.besitzer : "Frei";
  const intro = isPendingField(field.feld_id)
    ? `${escapeHtml(state.activePlayerName)} muss dieses Feld jetzt abschliessen.`
    : "Infoansicht fuer dieses Spielfeld.";

  return `
    <div class="hero-badge">${isPendingField(field.feld_id) ? "Aktive Aktion" : "Feldinfo"}</div>
    <h2>${escapeHtml(field.name)}</h2>
    <p class="modal-intro">${intro}</p>
    <div class="modal-meta">
      <div class="modal-row"><span>Typ</span><strong>${escapeHtml(field.typ)}</strong></div>
      <div class="modal-row"><span>Besitzer</span><strong>${escapeHtml(owner)}</strong></div>
      <div class="modal-row"><span>Kaufpreis</span><strong>${escapeHtml(field.kaufpreis || "-")}</strong></div>
      <div class="modal-row"><span>Miete</span><strong>${escapeHtml(field.miete || "-")}</strong></div>
      <div class="modal-row"><span>Getraenk</span><strong>${escapeHtml(field.alkohol_typ)} (${escapeHtml(field.alkohol_menge)})</strong></div>
      <div class="modal-row"><span>Regel</span><strong>${escapeHtml(field.zusatz_regel || "-")}</strong></div>
    </div>
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

      html.push(`
        <button
          type="button"
          class="field-tile${field.ist_kaufbar ? " field-buyable" : ""}${activeClass}${pendingClass}"
          style="background: ${escapeHtml(field.farbe_css)};"
          onclick="showFieldInfo(${field.feld_id})"
        >
          <span class="field-name">${escapeHtml(field.name)}</span>
          <span class="field-type">${escapeHtml(field.typ)}</span>
          ${owner}
          <div class="field-players">${tokens}</div>
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
  refs.ownershipCountChip.textContent = `${state.ownership.length} Besitzer`;
  if (!state.ownership.length) {
    refs.ownershipList.innerHTML = '<p class="empty-note">Noch hat niemand ein Feld gekauft.</p>';
    return;
  }

  refs.ownershipList.innerHTML = state.ownership.map(ownershipMarkup).join("");
}

function renderEventLog() {
  const entries = state.eventLog && state.eventLog.length
    ? state.eventLog.map(eventMarkup).join("")
    : '<p class="empty-note">Der Spielverlauf erscheint hier.</p>';
  refs.eventLog.innerHTML = entries;
}

function renderActionPanel() {
  const total = state.displayRoll ? state.displayRoll[0] + state.displayRoll[1] : null;
  const title = state.activePlayerName || "Runde";
  let body = "Bereit fuer den naechsten Zug.";
  let actions = `
    <button type="button" class="primary-btn" onclick="handleRoll()" ${busy ? "disabled" : ""}>Wuerfeln</button>
  `;

  if (state.phase === "move" && total !== null) {
    body = `${title} hat ${total} gewuerfelt und kann jetzt ziehen.`;
    actions = `
      <button type="button" class="primary-btn" onclick="handleMove()" ${busy ? "disabled" : ""}>Zug ausfuehren</button>
    `;
  } else if (state.phase === "field_action" && state.popupFeld) {
    body = `${title} ist auf ${state.popupFeld.name} gelandet. Bitte die Feldaktion abschliessen.`;
    actions = `
      <button type="button" class="primary-btn" onclick="showPendingField()" ${busy ? "disabled" : ""}>Feldaktion oeffnen</button>
    `;
  }

  if (state.lastEvent) {
    body = `${body} ${state.lastEvent}`;
  }

  refs.phaseChip.textContent = getPhaseChipText();
  refs.turnSummary.innerHTML = `
    <div class="turn-summary-hero">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(body)}</span>
    </div>
  `;
  refs.commandActions.innerHTML = actions;
  refs.currentFieldButton.disabled = state.phase !== "field_action" || busy;
}

function renderCenterCard() {
  refs.centerTitle.textContent = state.activePlayerName || "Bereit";
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
  renderActionPanel();
  renderCenterCard();
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
    throw new Error(data.msg || "Aktion konnte nicht ausgefuehrt werden.");
  }

  return data;
}

function animateDice(roll) {
  if (!roll) {
    return;
  }

  window.clearInterval(animationTimer);
  let count = 0;
  const maxCount = 12;

  refs.rollStatus.textContent = `${state.activePlayerName} wuerfelt...`;

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
      refs.rollStatus.textContent = `${state.activePlayerName} hat ${roll[0] + roll[1]} gewuerfelt.`;
    }
  }, 80);
}

function closeFieldModal() {
  selectedFieldId = null;
  renderModal();
}

function showFieldInfo(fieldId) {
  selectedFieldId = fieldId;
  renderModal();
}

function showPendingField() {
  if (!state.popupFeld) {
    return;
  }

  selectedFieldId = state.popupFeld.feld_id;
  renderModal();
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
  refs.currentFieldButton = document.getElementById("currentFieldButton");
  refs.playerCountChip = document.getElementById("playerCountChip");
  refs.ownershipCountChip = document.getElementById("ownershipCountChip");
  refs.centerTitle = document.getElementById("centerTitle");
  refs.centerCopy = document.getElementById("centerCopy");
  refs.rollStatus = document.getElementById("rollStatus");
  refs.toast = document.getElementById("toast");
  refs.w1 = document.getElementById("w1");
  refs.w2 = document.getElementById("w2");
}

function bindEvents() {
  refs.currentFieldButton.addEventListener("click", showPendingField);
  refs.modal.addEventListener("click", (event) => {
    if (event.target === refs.modal) {
      closeFieldModal();
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

window.closeFieldModal = closeFieldModal;
window.showFieldInfo = showFieldInfo;
window.showPendingField = showPendingField;
window.handleFieldAction = handleFieldAction;
window.handleRoll = handleRoll;
window.handleMove = handleMove;
