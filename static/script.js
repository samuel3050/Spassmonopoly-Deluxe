function wuerfeln() {
  document.getElementById("anzeige").innerText = "Würfeln...";
  let w1 = document.getElementById("w1");
  let w2 = document.getElementById("w2");

  // Animation durch zufällige Zahlen
  let interval = setInterval(() => {
    let z1 = Math.floor(Math.random() * 6) + 1;
    let z2 = Math.floor(Math.random() * 6) + 1;
    w1.src = `/static/dice/${z1}.png`;
    w2.src = `/static/dice/${z2}.png`;
  }, 100);

  // Nach 1 Sekunde stoppen und echtes Ergebnis holen
  setTimeout(() => {
    clearInterval(interval);
    fetch("/roll")
      .then(res => res.json())
      .then(data => {
        w1.src = `/static/dice/${data.w1}.png`;
        w2.src = `/static/dice/${data.w2}.png`;
        let text = `Gewürfelt: ${data.w1} + ${data.w2} = ${data.summe}`;
        if (data.doppel) {
          text += " (Doppel! Nochmal würfeln)";
        }
        document.getElementById("anzeige").innerText = text;
        document.getElementById("spielername").innerText = `${data.spieler} ist am Zug`;
      });
  }, 1000);
}
