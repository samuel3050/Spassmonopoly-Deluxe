const BOARD_COORDS = [
  [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [8, 0], [9, 0], [10, 0], [11, 0], [12, 0], [13, 0],
  [13, 1], [13, 2], [13, 3], [13, 4], [13, 5], [13, 6],
  [13, 7], [12, 7], [11, 7], [10, 7], [9, 7], [8, 7], [7, 7], [6, 7], [5, 7], [4, 7], [3, 7], [2, 7], [1, 7], [0, 7],
  [0, 6], [0, 5], [0, 4], [0, 3], [0, 2], [0, 1],
];
const BOARD_COLUMNS = 14;
const BOARD_ROWS = 8;

const refs = {};

let state = window.gameData;
let selectedFieldId = null;
let busy = false;
let toastTimer = null;
let diceTimer = null;
let pollTimer = null;
let lastSignature = "";
let previousPositions = [...(state.positionen || [])];
let eventSearchTerm = "";
let eventTypeFilter = "all";
let winnerAcknowledged = false;
let userSettings = {
  volume: "70",
  animations: "on",
  theme: "dark",
  speed: "normal",
  ...(window.appSettings || {}),
};
let audio = null;
let lastAudioEventId = state.lastEventEntry?.id || null;

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

function animationsEnabled() {
  return userSettings.animations !== "off";
}

function speedScale() {
  if (userSettings.speed === "slow") return 1.45;
  if (userSettings.speed === "fast") return 0.65;
  if (userSettings.speed === "instant") return 0.05;
  return 1;
}

function scaledDuration(value) {
  return Math.max(5, Math.round(value * speedScale()));
}

function applyUserSettings(settings = userSettings) {
  userSettings = { ...userSettings, ...settings };
  audio?.setSettings(userSettings);
  document.body.classList.toggle("theme-light", userSettings.theme === "light");
  document.body.classList.toggle("theme-dark", userSettings.theme !== "light");
  document.body.classList.toggle("reduce-motion", !animationsEnabled());
  document.documentElement.style.setProperty("--motion-speed", String(speedScale()));
}

function playGameEvent(event) {
  if (!event?.id || event.id === lastAudioEventId) return;
  lastAudioEventId = event.id;
  if (event.type === "dice_roll") return;
  audio?.play(audio.eventSound(event.type));
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
  return "Würfeln";
}

function getActionCopy() {
  if (state.gameStatus === "finished") {
    return state.lastEvent || "Die Runde ist beendet.";
  }
  if (state.phase === "move" && state.displayRoll) {
    return `${state.activePlayerName} hat ${state.displayRoll[0] + state.displayRoll[1]} gewürfelt. Jetzt wird gezogen.`;
  }
  if (state.phase === "field_action" && state.popupFeld) {
    return state.popupHint || `${state.activePlayerName} wertet ${state.popupFeld.name} aus.`;
  }
  return `${state.activePlayerName || "Der aktive Spieler"} ist bereit für den nächsten Wurf.`;
}

function getInsightCopy(field) {
  if (!field) return "Wähle ein Feld aus, um Details zu sehen.";
  if (state.popupHint && isPendingField(field.feld_id)) return state.popupHint;
  if (field.besitzer) return `${field.name} gehört ${field.besitzer}.`;
  if (field.ist_kaufbar) return `${field.name} ist frei und kann beim Besuch gesichert werden.`;
  return field.zusatz_regel || "Dieses Feld hat keinen zusätzlichen Effekt.";
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
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('miete', ${field.feld_id})">Abgabe bestätigen</button>`;
  }
  if (isSpecialActionField(field)) {
    return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Effekt auslösen</button>`;
  }
  return `<button type="button" class="primary-btn" onclick="handleFieldAction('skip', ${field.feld_id})">Zug abschliessen</button>`;
}

function createFieldDetails(field) {
  const owner = field.besitzer || "Noch frei";
  const active = isPendingField(field.feld_id);
  const intro = active ? `${state.activePlayerName} steht aktuell hier.` : "Detailansicht für dieses Feld.";
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

function buildPrimaryActionMarkup(location = "center") {
  const canAct = state.canAct !== false && state.gameStatus !== "finished";
  const disabled = busy || !canAct;

  if (state.gameStatus === "finished") {
    return '<button type="button" class="primary-btn" disabled>Runde beendet</button>';
  }
  if (state.phase === "move") {
    return `<button type="button" class="primary-btn" onclick="handleMove()" ${disabled ? "disabled" : ""}>${canAct ? "Figur bewegen" : "Warten"}</button>`;
  }
  if (state.phase === "field_action" && state.popupFeld) {
    return `<button type="button" class="primary-btn" onclick="showPendingField()" ${busy ? "disabled" : ""}>Feld öffnen</button>`;
  }

  const label = canAct ? (location === "mirror" ? "Jetzt würfeln" : "Würfeln") : "Warten";
  return `<button type="button" class="primary-btn" onclick="handleRoll()" ${disabled ? "disabled" : ""}>${label}</button>`;
}

function renderQuickStats() {
  const highlights = state.highlights || {};
  refs.quickStats.innerHTML = [
    statCardMarkup("Runde", `#${highlights.runde || 1}`, "Aktuell"),
    statCardMarkup("Zug", `#${highlights.zugnummer || 1}`, "Gesamt"),
    statCardMarkup("Spitze", highlights.leaderName || "Offen", highlights.leaderName ? `${highlights.leaderCount} Felder` : "Keine Führung"),
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
  const title = state.activePlayerName || "Bereit";

  refs.phaseChip.textContent = getPhaseLabel();
  refs.centerPlayerName.textContent = title;
  if (refs.topActivePlayer) refs.topActivePlayer.textContent = title ? `Am Zug: ${title}` : "Bereit";
  refs.currentFieldButton.disabled = state.phase !== "field_action" || busy;
  refs.turnSummary.innerHTML = `
    <div class="turn-summary-hero">
      <strong>${escapeHtml(title)}</strong>
      <span>${escapeHtml(getActionCopy())}</span>
    </div>
  `;
  refs.commandActions.innerHTML = buildPrimaryActionMarkup("center");
  if (refs.actionMirror) {
    refs.actionMirror.innerHTML = `
      <div class="action-mirror-copy">${escapeHtml(getActionCopy())}</div>
      ${buildPrimaryActionMarkup("mirror")}
    `;
  }
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
  renderWinnerModal();
  renderAdminVisibility();
}

function setState(nextState, options = {}) {
  state = nextState;
  window.gameData = nextState;

  if (options.closeModal) selectedFieldId = null;
  if (options.openPending && nextState.popupFeld) selectedFieldId = nextState.popupFeld.feld_id;
  if (selectedFieldId && !getField(selectedFieldId)) selectedFieldId = null;

  renderApp();
  playGameEvent(nextState.lastEventEntry);
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
  toastTimer = window.setTimeout(() => refs.toast.classList.remove("show"), scaledDuration(2400));
}

function getWinnerName() {
  const event = state.lastEventEntry || {};
  if (event.type === "winner" && event.player_id) {
    const player = state.canonicalState?.players?.find((entry) => entry.id === event.player_id);
    if (player?.name) return player.name;
  }
  const match = String(state.lastEvent || "").match(/Gewinner:\s*([^\n]+?)\s+gewinnt/i);
  return match ? match[1] : (state.highlights?.leaderName || state.activePlayerName || "Gewinner");
}

function renderWinnerModal() {
  if (!refs.winnerModal) return;
  if (state.gameStatus !== "finished" || winnerAcknowledged) {
    refs.winnerModal.classList.remove("open");
    refs.winnerModal.setAttribute("aria-hidden", "true");
    return;
  }
  refs.winnerTitle.textContent = `${getWinnerName()} gewinnt`;
  refs.winnerCopy.textContent = state.lastEvent || "Die Runde ist beendet.";
  refs.winnerModal.classList.add("open");
  refs.winnerModal.setAttribute("aria-hidden", "false");
}

async function postJson(url, payload = null) {
  const options = { method: "POST", headers: { "Content-Type": "application/json" } };
  if (payload) options.body = JSON.stringify(payload);
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || !data.ok) {
    const error = new Error(data.msg || "Aktion konnte nicht ausgeführt werden.");
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
  if (!animationsEnabled()) {
    refs.w1.src = `/static/dice/${roll[0]}.png`;
    refs.w2.src = `/static/dice/${roll[1]}.png`;
    refs.diceDisplay.classList.remove("rolling");
    refs.rollStatus.textContent = `${state.activePlayerName} hat ${roll[0] + roll[1]} gewürfelt.`;
    audio?.play("dice");
    return;
  }
  let ticks = 0;
  refs.diceDisplay.classList.add("rolling");
  refs.rollStatus.textContent = `${state.activePlayerName} würfelt ...`;

  diceTimer = window.setInterval(() => {
    refs.w1.src = `/static/dice/${Math.floor(Math.random() * 6) + 1}.png`;
    refs.w2.src = `/static/dice/${Math.floor(Math.random() * 6) + 1}.png`;
    ticks += 1;
    if (ticks >= 11) {
      window.clearInterval(diceTimer);
      refs.w1.src = `/static/dice/${roll[0]}.png`;
      refs.w2.src = `/static/dice/${roll[1]}.png`;
      refs.diceDisplay.classList.remove("rolling");
      refs.rollStatus.textContent = `${state.activePlayerName} hat ${roll[0] + roll[1]} gewürfelt.`;
      audio?.play("dice");
    }
  }, scaledDuration(65));
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

function openExitModal() {
  if (!state.isHost) {
    showToast("Nur der Host darf das Spiel beenden.");
    audio?.play("warn");
    return;
  }
  refs.exitModal.classList.add("open");
  refs.exitModal.setAttribute("aria-hidden", "false");
}

function closeExitModal() {
  refs.exitModal.classList.remove("open");
  refs.exitModal.setAttribute("aria-hidden", "true");
}

function openSaveModal() {
  if (!state.isHost) {
    showToast("Nur der Host darf speichern.");
    audio?.play("warn");
    return;
  }
  refs.saveModal.classList.add("open");
  refs.saveModal.setAttribute("aria-hidden", "false");
  refs.manualSaveName.focus();
}

function closeSaveModal() {
  refs.saveModal.classList.remove("open");
  refs.saveModal.setAttribute("aria-hidden", "true");
}

function closeWinnerModal() {
  winnerAcknowledged = true;
  refs.winnerModal?.classList.remove("open");
  refs.winnerModal?.setAttribute("aria-hidden", "true");
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
    audio?.play("warn");
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
    audio?.play("move");
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
    showToast(error.message);
    audio?.play("warn");
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
    const fieldEvent = data.state.eventLog?.[data.state.eventLog.length - 2];
    audio?.play(fieldEvent?.type === "card_event" ? "card" : "success");
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
    showToast(error.message);
    audio?.play("warn");
  } finally {
    setBusy(false);
  }
}

function saveGame() {
  if (!state.isHost) {
    showToast("Nur der Host darf speichern.");
    audio?.play("warn");
    return;
  }
  openSaveModal();
}

async function submitSaveGame() {
  if (!state.isHost) {
    showToast("Nur der Host darf speichern.");
    audio?.play("warn");
    return;
  }
  if (busy) return;
  const name = refs.manualSaveName.value.trim();
  if (name.length < 2) {
    showToast("Bitte gib mindestens 2 Zeichen ein.");
    audio?.play("warn");
    return;
  }
  setBusy(true);
  try {
    const data = await postJson("/api/save-current", { name });
    closeSaveModal();
    setState(data.state, { toast: data.message || "Spielstand gespeichert." });
    lastSignature = getStateSignature(data.state);
    audio?.play("save");
  } catch (error) {
    if (error.state) {
      setState(error.state);
      lastSignature = getStateSignature(error.state);
    }
    showToast(error.message);
    audio?.play("warn");
  } finally {
    setBusy(false);
  }
}

async function exitGame(mode) {
  if (!state.isHost) {
    showToast("Nur der Host darf das Spiel beenden.");
    audio?.play("warn");
    return;
  }
  if (busy) return;
  setBusy(true);
  try {
    const data = await postJson("/api/exit-game", { mode });
    audio?.play("save");
    window.location.href = data.redirect_url || "/";
  } catch (error) {
    showToast(error.message);
    audio?.play("warn");
    closeExitModal();
  } finally {
    setBusy(false);
  }
}

function cacheRefs() {
  refs.modal = document.getElementById("fieldModal");
  refs.exitModal = document.getElementById("exitModal");
  refs.saveModal = document.getElementById("saveModal");
  refs.winnerModal = document.getElementById("winnerModal");
  refs.winnerTitle = document.getElementById("winnerTitle");
  refs.winnerCopy = document.getElementById("winnerCopy");
  refs.manualSaveName = document.getElementById("manualSaveName");
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
  refs.saveGameButton = document.getElementById("saveGameButton");
  refs.exitGameButton = document.getElementById("exitGameButton");
  refs.hostOnlyControls = document.querySelectorAll("[data-host-only]");
  refs.playerCountChip = document.getElementById("playerCountChip");
  refs.ownershipCountChip = document.getElementById("ownershipCountChip");
  refs.centerTitle = document.getElementById("centerTitle");
  refs.centerPlayerName = document.getElementById("centerPlayerName");
  refs.topActivePlayer = document.getElementById("topActivePlayer");
  refs.centerCopy = document.getElementById("centerCopy");
  refs.rollStatus = document.getElementById("rollStatus");
  refs.boardInsights = document.getElementById("boardInsights");
  refs.actionMirror = document.getElementById("actionMirror");
  refs.toast = document.getElementById("toast");
  refs.w1 = document.getElementById("w1");
  refs.w2 = document.getElementById("w2");
  refs.diceDisplay = document.getElementById("diceDisplay");
}

function renderAdminVisibility() {
  refs.hostOnlyControls?.forEach((element) => {
    const isHost = state.isHost === true;
    element.hidden = !isHost;
    if ("disabled" in element) element.disabled = !isHost;
    element.querySelectorAll?.("button,input,select").forEach((control) => {
      control.disabled = !isHost;
    });
  });
}

function bindEvents() {
  document.addEventListener("pointerdown", () => {
    audio?.unlock();
    audio?.startMusic();
  }, { once: true });
  document.addEventListener("keydown", () => {
    audio?.unlock();
    audio?.startMusic();
  }, { once: true });
  document.addEventListener("click", (event) => {
    if (event.target.closest("button,a")) {
      audio?.unlock();
      audio?.play("button");
    }
  });
  refs.currentFieldButton.addEventListener("click", showPendingField);
  refs.saveGameButton.addEventListener("click", saveGame);
  refs.exitGameButton.addEventListener("click", openExitModal);
  refs.modal.addEventListener("click", (event) => {
    if (event.target === refs.modal) closeFieldModal();
  });
  refs.exitModal.addEventListener("click", (event) => {
    if (event.target === refs.exitModal) closeExitModal();
  });
  refs.saveModal.addEventListener("click", (event) => {
    if (event.target === refs.saveModal) closeSaveModal();
  });
  refs.winnerModal?.addEventListener("click", (event) => {
    if (event.target === refs.winnerModal) closeWinnerModal();
  });
  refs.eventSearch.addEventListener("input", (event) => {
    eventSearchTerm = event.target.value.trim().toLowerCase();
    renderEventLog();
  });
  refs.eventFilter.addEventListener("change", (event) => {
    eventTypeFilter = event.target.value;
    renderEventLog();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeFieldModal();
      closeExitModal();
      closeSaveModal();
      closeWinnerModal();
    }
  });
}

function bootBoard() {
  cacheRefs();
  audio = new AudioManager(userSettings);
  applyUserSettings();
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
window.addEventListener("pagehide", () => {
  audio?.stopMusic();
  window.clearInterval(pollTimer);
  window.clearInterval(diceTimer);
  window.clearTimeout(toastTimer);
});

window.closeFieldModal = closeFieldModal;
window.closeExitModal = closeExitModal;
window.closeSaveModal = closeSaveModal;
window.closeWinnerModal = closeWinnerModal;
window.showFieldInfo = showFieldInfo;
window.showPendingField = showPendingField;
window.handleFieldAction = handleFieldAction;
window.handleRoll = handleRoll;
window.handleMove = handleMove;
window.saveGame = saveGame;
window.submitSaveGame = submitSaveGame;
window.exitGame = exitGame;
