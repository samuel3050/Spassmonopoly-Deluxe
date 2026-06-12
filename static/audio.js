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
  }

  setSettings(settings = {}) {
    this.settings = { ...this.settings, ...settings };
    if (this.master) {
      this.master.gain.value = this.masterVolume();
    }
    if (this.music) {
      this.music.gain.gain.value = Math.max(0.0001, this.musicVolume() * 0.12);
    }
    if (this._audioEl) {
      this._audioEl.volume = Math.max(0, Math.min(1, this.musicVolume()));
    }
    if (this.started && !this.music && this.masterVolume() && this.musicVolume()) {
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

  async startMusic() {
    if (!this.masterVolume() || !this.musicVolume() || this.music) return;
    try {
      const context = this.ensureContext();
      const gain = context.createGain();
      gain.gain.value = Math.max(0.0001, this.musicVolume() * 0.12);
      gain.connect(this.master);

      let tracks = [];
      try {
        const resp = await fetch('/api/music/playlist');
        if (resp.ok) {
          const data = await resp.json();
          tracks = data.tracks || [];
        }
      } catch (e) {
        tracks = [];
      }

      if (!tracks.length) {
        this._startAmbientFallback(context, gain);
        return;
      }

      this._playlist = [...tracks].sort(() => Math.random() - 0.5);
      this._trackIndex = 0;
      this._musicContext = context;
      this._musicGain = gain;
      this.music = { gain, playlist: this._playlist };
      this._playNextTrack();
    } catch (error) {
      return;
    }
  }

  _playNextTrack() {
    if (!this._playlist || !this._playlist.length) return;
    try {
      if (this._audioEl) {
        try { this._audioEl.pause(); } catch (e) {}
        try { this._audioElSource?.disconnect(); } catch (e) {}
        this._audioEl = null;
      }
      const url = this._playlist[this._trackIndex];
      const audioEl = new Audio(url);
      audioEl.crossOrigin = 'anonymous';
      audioEl.preload = 'auto';

      const context = this._musicContext;
      const gain = this._musicGain;
      if (context && gain) {
        try {
          const src = context.createMediaElementSource(audioEl);
          src.connect(gain);
          this._audioElSource = src;
        } catch (e) {
          audioEl.volume = Math.max(0, Math.min(1, this.musicVolume()));
        }
      } else {
        audioEl.volume = Math.max(0, Math.min(1, this.musicVolume()));
      }

      audioEl.addEventListener('ended', () => {
        if (!this.music) return;
        this._trackIndex = (this._trackIndex + 1) % this._playlist.length;
        this._playNextTrack();
      });

      const play = async () => {
        try {
          if (context && context.state === 'suspended') await context.resume();
          await audioEl.play();
        } catch (e) {
          // autoplay policy - will retry on next user interaction
        }
      };
      play();
      this._audioEl = audioEl;
      if (this.music) this.music.audioEl = audioEl;
    } catch (e) {
      this._startAmbientFallback(this._musicContext, this._musicGain);
    }
  }

  stopMusic() {
    if (!this.music) return;
    try {
      if (this._audioEl) {
        try { this._audioEl.pause(); } catch (e) {}
        try { this._audioElSource?.disconnect(); } catch (e) {}
        this._audioEl = null;
        this._audioElSource = null;
      }
      if (this.music.oscillators) {
        this.music.oscillators.forEach((osc) => {
          try { osc.stop(); } catch (e) {}
        });
      }
      try { this.music.gain.disconnect(); } catch (e) {}
    } finally {
      this.music = null;
      this._playlist = null;
      this._trackIndex = 0;
    }
  }

  createLoopOscillator(context, type, frequency, output) {
    const oscillator = context.createOscillator();
    oscillator.type = type;
    oscillator.frequency.value = frequency;
    oscillator.connect(output);
    return oscillator;
  }

  _startAmbientFallback(context, gain) {
    if (!context || !gain) return;
    try {
      const low = context.createOscillator();
      low.type = 'sine';
      low.frequency.value = 60;
      const mid = context.createOscillator();
      mid.type = 'triangle';
      mid.frequency.value = 110;
      const lp = context.createBiquadFilter();
      lp.type = 'lowpass';
      lp.frequency.value = 800;
      const padGain = context.createGain();
      padGain.gain.value = 0.0015 * (this.musicVolume() || 1);
      low.connect(lp);
      mid.connect(lp);
      lp.connect(padGain);
      padGain.connect(gain);
      low.start();
      mid.start();
      this.music = { gain, oscillators: [low, mid], fallback: true };
    } catch (e) {
      this.music = null;
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
