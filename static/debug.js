(function () {
  const params = new URLSearchParams(window.location.search);
  const enabled = params.get("debug") === "1" || window.localStorage.getItem("spassDebug") === "1";

  window.spassDebugEnabled = enabled;
  window.debugLog = function debugLog(scope, event, data = {}) {
    if (!enabled) return;
    const payload = {
      scope,
      event,
      timestamp: new Date().toISOString(),
      ...data,
    };
    console.debug("[SpassDebug]", payload);
  };

  window.debugLog("debug", "enabled", {
    path: window.location.pathname,
  });
})();
