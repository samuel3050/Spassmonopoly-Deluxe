function wuerfeln() {
    const btn = document.getElementById('wuerfelnBtn');
    if (btn) btn.disabled = true;
    const form = document.getElementById('wuerfelform');
    if (form) form.submit();
    return false;
}

// Feld kaufen Popup: "Kaufpreis bezahlt" mit Button
window.addEventListener("DOMContentLoaded", function() {
    setTimeout(() => {
        // Beispiel für das Kaufen-Button-Handling:
        const kaufenBtn = document.getElementById('kaufen-btn');
        if (kaufenBtn) {
            kaufenBtn.onclick = function() {
                const feldId = kaufenBtn.getAttribute('data-feld');
                fetch('/feld_aktion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({aktion: 'kaufen', feld: feldId})
                }).then(res => res.json()).then(() => {
                    document.getElementById('feld-modal').innerHTML = `
                        <h3>Kaufpreis bezahlt!</h3>
                        <button id="bezahlt-btn" style="margin-top:18px;">Bezahlt</button>
                    `;
                    document.getElementById('feld-modal').style.display = 'block';
                    document.getElementById('bezahlt-btn').onclick = function() {
                        document.getElementById('feld-modal').style.display = 'none';
                        setTimeout(() => location.reload(), 200);
                    };
                });
            };
        }
        const mieteBtn = document.getElementById('miete-btn');
        if (mieteBtn) {
            mieteBtn.onclick = function() {
                fetch('/feld_aktion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({aktion: 'miete', feld: mieteBtn.getAttribute('data-feld')})
                }).then(res => res.json()).then(() => {
                    document.getElementById('feld-modal').style.display = 'none';
                    setTimeout(() => location.reload(), 400);
                });
            };
        }
        const skipBtn = document.getElementById('skip-btn');
        if (skipBtn) {
            skipBtn.onclick = function() {
                fetch('/feld_aktion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({aktion: 'skip', feld: skipBtn.getAttribute('data-feld')})
                }).then(() => {
                    document.getElementById('feld-modal').style.display = 'none';
                    setTimeout(() => location.reload(), 400);
                });
            };
        }
    }, 100);
});
