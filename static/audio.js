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
      this.music.gain.gain.value = this.musicVolume() * 0.22;
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

  startMusic() {
    if (!this.masterVolume() || !this.musicVolume() || this.music) return;
    try {
      const context = this.ensureContext();
      const gain = context.createGain();
      gain.gain.value = this.musicVolume() * 0.22;
      gain.connect(this.master);
      const bass = this.createLoopOscillator(context, "sine", 110, gain);
      const pad = this.createLoopOscillator(context, "triangle", 220, gain);
      bass.start();
      pad.start();
      this.music = { gain, oscillators: [bass, pad] };
    } catch (error) {
      return;
    }
  }

  stopMusic() {
    if (!this.music) return;
    this.music.oscillators.forEach((oscillator) => oscillator.stop());
    this.music.gain.disconnect();
    this.music = null;
  }

  createLoopOscillator(context, type, frequency, output) {
    const oscillator = context.createOscillator();
    oscillator.type = type;
    oscillator.frequency.value = frequency;
    oscillator.connect(output);
    return oscillator;
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
