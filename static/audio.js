class AudioManager {
  constructor(settings = {}) {
    this.settings = {
      volume: "70",
      music_volume: "35",
      effects_volume: "80",
      muted: "off",
      ...settings,
    };
    this.context = null;
    this.master = null;
    this.music = null;
    this.started = false;
    this._audioEl = null;
    this._playlist = null;
    this._trackIndex = 0;
    this._musicStarting = false;
    this._lastPersist = 0;
    this._storageKey = "sm_music_state";
  }

  setSettings(settings = {}) {
    this.settings = { ...this.settings, ...settings };
    if (this.master) {
      this.master.gain.value = this.masterVolume();
    }
    if (this._audioEl) {
      this._audioEl.volume = this._effectiveMusicVolume();
      if (this._effectiveMusicVolume() > 0 && this._audioEl.paused) {
        this._tryPlay();
      }
    } else if (this.masterVolume() > 0 && this.musicVolume() > 0) {
      this.startMusic();
    }
  }

  masterVolume() {
    if (this.settings.muted === "on") return 0;
    return Math.max(0, Math.min(100, Number(this.settings.volume || 0))) / 100;
  }

  musicVolume() {
    return Math.max(0, Math.min(100, Number(this.settings.music_volume || 0))) / 100;
  }

  effectsVolume() {
    return Math.max(0, Math.min(100, Number(this.settings.effects_volume || 0))) / 100;
  }

  ensureContext() {
    if (!this.context) {
      this.context = new (window.AudioContext || window.webkitAudioContext)();
      this.master = this.context.createGain();
      this.master.connect(this.context.destination);
      this.setSettings();
    }
    if (this.context.state === "suspended") {
      this.context.resume();
    }
    return this.context;
  }

  unlock() {
    try {
      this.ensureContext();
      this.started = true;
    } catch (error) {
      return;
    }
  }

  play(name = "button") {
    if (!this.masterVolume() || !this.effectsVolume()) return;
    try {
      const context = this.ensureContext();
      const profile = this.soundProfile(name);
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = profile.type;
      oscillator.frequency.setValueAtTime(profile.frequency, context.currentTime);
      if (profile.endFrequency) {
        oscillator.frequency.exponentialRampToValueAtTime(profile.endFrequency, context.currentTime + profile.duration);
      }
      gain.gain.setValueAtTime(profile.gain * this.effectsVolume(), context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + profile.duration);
      oscillator.connect(gain);
      gain.connect(this.master);
      oscillator.start();
      oscillator.stop(context.currentTime + profile.duration);
    } catch (error) {
      return;
    }
  }

  // Background music runs through a plain <audio> element (decoupled from the
  // Web Audio effects graph) so it keeps looping reliably and can resume across
  // page navigations via a persisted playback position.
  _effectiveMusicVolume() {
    return Math.max(0, Math.min(1, this.masterVolume() * this.musicVolume()));
  }

  _tryPlay() {
    if (!this._audioEl) return;
    const promise = this._audioEl.play();
    if (promise && typeof promise.catch === "function") {
      // Autoplay can be blocked until the first user gesture; the global
      // interaction listeners retry startMusic(), so swallow the rejection.
      promise.catch(() => {});
    }
  }

  // Wires up every realistic resume trigger so background music behaves as one
  // continuous loop across the multi-page app: it retries on load, on tab focus,
  // on the first gesture, and on bfcache restores, and saves its position before
  // each navigation so the next page resumes exactly where this one left off.
  enableContinuousPlayback() {
    if (this._continuousBound) return;
    // The persistent top-level shell owns the looping music. Inside the app
    // iframe we only play sound effects, so skip music wiring here to avoid a
    // second, duplicate stream.
    if (window.self !== window.top) return;
    this._continuousBound = true;
    const resume = () => this.startMusic();
    document.addEventListener("pointerdown", () => { this.unlock(); resume(); }, { once: true });
    document.addEventListener("keydown", () => { this.unlock(); resume(); }, { once: true });
    window.addEventListener("pageshow", resume);
    window.addEventListener("focus", resume);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") resume();
    });
    window.addEventListener("pagehide", () => this.stopMusic());
    window.addEventListener("beforeunload", () => this._persistState(true));
    resume();
  }

  startMusic() {
    // Looping music belongs to the persistent top-level shell only; inside the
    // app iframe this is a no-op so there is never a second stream.
    if (window.self !== window.top) return;
    if (this._audioEl) {
      this._tryPlay();
      return;
    }
    const cached = this._cachedTracks();
    if (cached) {
      // Synchronous path (playlist already known): stays inside the current user
      // gesture so the autoplay policy is far more likely to permit playback.
      if (cached.length) this._beginPlayback(cached);
      return;
    }
    this._fetchAndStart();
  }

  _fetchAndStart() {
    if (this._musicStarting) return;
    this._musicStarting = true;
    fetch("/api/music/playlist")
      .then((resp) => (resp.ok ? resp.json() : { tracks: [] }))
      .then((data) => {
        const tracks = data.tracks || [];
        this._cacheTracks(tracks);
        if (tracks.length && !this._audioEl) this._beginPlayback(tracks);
      })
      .catch(() => {})
      .finally(() => { this._musicStarting = false; });
  }

  _beginPlayback(tracks) {
    if (this._audioEl || !tracks || !tracks.length) return;
    this._playlist = tracks;
    const saved = this._restoreState();
    this._trackIndex =
      saved && Number.isInteger(saved.index) && saved.index >= 0 && saved.index < tracks.length
        ? saved.index
        : 0;
    const resumeAt = saved && saved.url === this._playlist[this._trackIndex] ? saved.position || 0 : 0;
    this._loadTrack(resumeAt);
  }

  _cachedTracks() {
    try {
      const raw = localStorage.getItem("sm_music_tracks");
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  _cacheTracks(tracks) {
    try {
      localStorage.setItem("sm_music_tracks", JSON.stringify(tracks || []));
    } catch (e) {
      // storage unavailable; the next page just refetches the playlist.
    }
  }

  _loadTrack(startAt = 0) {
    if (!this._playlist || !this._playlist.length) return;
    if (this._audioEl) {
      try { this._audioEl.pause(); } catch (e) {}
      this._audioEl = null;
    }
    const audioEl = new Audio(this._playlist[this._trackIndex]);
    audioEl.preload = "auto";
    audioEl.loop = this._playlist.length === 1;
    audioEl.volume = this._effectiveMusicVolume();

    audioEl.addEventListener("loadedmetadata", () => {
      if (startAt > 0 && Number.isFinite(audioEl.duration) && startAt < audioEl.duration) {
        try { audioEl.currentTime = startAt; } catch (e) {}
      }
    });
    audioEl.addEventListener("timeupdate", () => this._persistState());
    audioEl.addEventListener("ended", () => {
      if (audioEl.loop) return;
      this._trackIndex = (this._trackIndex + 1) % this._playlist.length;
      this._loadTrack(0);
    });

    this._audioEl = audioEl;
    this.music = { audioEl };
    this._tryPlay();
  }

  stopMusic() {
    this._persistState(true);
    if (this._audioEl) {
      try { this._audioEl.pause(); } catch (e) {}
    }
  }

  _persistState(force = false) {
    if (!this._audioEl || !this._playlist) return;
    const now = Date.now();
    if (!force && now - this._lastPersist < 900) return;
    this._lastPersist = now;
    try {
      localStorage.setItem(
        this._storageKey,
        JSON.stringify({
          index: this._trackIndex,
          url: this._playlist[this._trackIndex],
          position: this._audioEl.currentTime || 0,
          ts: now,
        })
      );
    } catch (e) {
      // storage may be unavailable (private mode); continuity simply degrades.
    }
  }

  _restoreState() {
    try {
      const raw = localStorage.getItem(this._storageKey);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  eventSound(eventType) {
    const map = {
      game_start: "start",
      dice_roll: "dice",
      movement: "move",
      card_event: "card",
      field_purchase: "success",
      manual_save: "save",
      game_exit: "save",
      turn_change: "turn",
      winner: "winner",
      error: "warn",
    };
    return map[eventType] || "button";
  }

  soundProfile(name) {
    const profiles = {
      button: { frequency: 440, duration: 0.08, gain: 0.09, type: "sine" },
      dice: { frequency: 260, endFrequency: 620, duration: 0.16, gain: 0.1, type: "square" },
      move: { frequency: 360, endFrequency: 500, duration: 0.11, gain: 0.075, type: "triangle" },
      save: { frequency: 660, duration: 0.13, gain: 0.08, type: "triangle" },
      success: { frequency: 720, duration: 0.12, gain: 0.08, type: "triangle" },
      start: { frequency: 520, endFrequency: 780, duration: 0.18, gain: 0.08, type: "triangle" },
      turn: { frequency: 490, duration: 0.1, gain: 0.06, type: "sine" },
      card: { frequency: 580, endFrequency: 760, duration: 0.14, gain: 0.075, type: "triangle" },
      winner: { frequency: 880, endFrequency: 1320, duration: 0.22, gain: 0.09, type: "triangle" },
      warn: { frequency: 220, duration: 0.16, gain: 0.06, type: "square" },
    };
    return profiles[name] || profiles.button;
  }
}

window.AudioManager = AudioManager;
