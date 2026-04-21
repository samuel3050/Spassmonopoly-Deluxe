-- Spa?monopoly Deluxe ? Datenbankschema
DROP DATABASE IF EXISTS spassmonopoly;
CREATE DATABASE spassmonopoly CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE spassmonopoly;

DROP TABLE IF EXISTS spielfelder;
CREATE TABLE spielfelder (
  feld_id INT NOT NULL PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  typ VARCHAR(30) NOT NULL,
  kaufpreis VARCHAR(20) DEFAULT NULL,
  miete VARCHAR(20) DEFAULT NULL,
  farbe VARCHAR(20) DEFAULT NULL,
  alkohol_typ VARCHAR(30) NOT NULL,
  alkohol_menge VARCHAR(30) NOT NULL,
  zusatz_regel VARCHAR(255) DEFAULT NULL,
  besitzer VARCHAR(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO spielfelder (feld_id, name, typ, kaufpreis, miete, farbe, alkohol_typ, alkohol_menge, zusatz_regel, besitzer) VALUES
  ('1', 'Los', 'Los', NULL, NULL, 'Dunkelgrau', 'Startbonus', '1 Punkt', 'Alle starten gemeinsam. Wer hier landet, bekommt neuen Schwung für die nächste Runde.', NULL),
  ('2', 'Lächelallee', 'Straße', '2 Punkte', '1 Punkt', 'Braun', 'Stimmung', 'Locker', 'Ein schneller Icebreaker bringt alle sofort ins Spiel.', NULL),
  ('3', 'Konfettiplatz', 'Straße', '3 Punkte', '2 Punkte', 'Braun', 'Showmoment', '2 Punkte', 'Feiere deinen Zug mit einer spontanen Miniaufgabe oder einer kleinen Jubelrunde.', NULL),
  ('4', 'Gemeinschaftspark', 'Gemeinschaft', NULL, NULL, 'Braun', 'Team', 'Gemeinsam', 'Alle denken sich zusammen eine kurze freundliche Gemeinschaftsaktion aus.', NULL),
  ('5', 'Sonnenpromenade', 'Straße', '5 Punkte', '3 Punkte', 'Braun', 'Energie', '3 Punkte', 'Ein strahlendes Feld mit starkem Auftakt für aktive Spielerinnen und Spieler.', NULL),
  ('6', 'Glücksgasse', 'Straße', '4 Punkte', '2 Punkte', 'Hellblau', 'Glück', '2 Punkte', 'Wer hier landet, erzählt kurz seinen bisher besten Spielzug.', NULL),
  ('7', 'Bühnenviertel', 'Straße', '5 Punkte', '3 Punkte', 'Hellblau', 'Auftritt', '3 Punkte', 'Eine kleine Geste oder Pose bringt Extra-Atmosphäre an den Tisch.', NULL),
  ('8', 'Musikmarkt', 'Straße', '6 Punkte', '4 Punkte', 'Hellblau', 'Rhythmus', '4 Punkte', 'Summt kurz einen Song, den alle kennen könnten.', NULL),
  ('9', 'Festivalforum', 'Straße', '7 Punkte', '5 Punkte', 'Hellblau', 'Publikum', '5 Punkte', 'Hier darf laut gejubelt werden: ein echtes Highlight im frühen Spiel.', NULL),
  ('10', 'Ideenjoker', 'Spezial', NULL, NULL, 'Rainbow', 'Joker', 'Freiwahl', 'Wähle für deinen nächsten Zug eine beliebige freundliche Kreativaktion.', NULL),
  ('11', 'Kreativkai', 'Straße', '6 Punkte', '4 Punkte', 'Pink', 'Idee', '4 Punkte', 'Nenne etwas, das heute für gute Laune gesorgt hat.', NULL),
  ('12', 'Designpassage', 'Straße', '7 Punkte', '5 Punkte', 'Pink', 'Stil', '5 Punkte', 'Ein Feld mit klarer Linie und starkem Auftritt.', NULL),
  ('13', 'Studiozeile', 'Straße', '8 Punkte', '6 Punkte', 'Pink', 'Kreativität', '6 Punkte', 'Erfinde in einem Satz einen Titel für eure heutige Runde.', NULL),
  ('14', 'Lichtbogen', 'Straße', '9 Punkte', '7 Punkte', 'Pink', 'Glanz', '7 Punkte', 'Ein besonders sichtbares Feld für starke Zwischensprints.', NULL),
  ('15', 'Glanzgalerie', 'Straße', '10 Punkte', '8 Punkte', 'Pink', 'Finale', '8 Punkte', 'Teile kurz deinen Lieblingsmoment der Partie.', NULL),
  ('16', 'Abenteuerring', 'Straße', '6 Punkte', '4 Punkte', 'Orange', 'Tempo', '4 Punkte', 'Behalte den Schwung: dieses Feld steht für mutige Züge.', NULL),
  ('17', 'Entdeckerweg', 'Straße', '7 Punkte', '5 Punkte', 'Orange', 'Entdeckung', '5 Punkte', 'Nenne einen Ort, den du gerne einmal besuchen würdest.', NULL),
  ('18', 'Teamspielplatz', 'Straße', '8 Punkte', '6 Punkte', 'Orange', 'Teamgeist', '6 Punkte', 'Kurze Mini-Challenge zu zweit oder in der Gruppe.', NULL),
  ('19', 'Rätselresidenz', 'Straße', '9 Punkte', '7 Punkte', 'Orange', 'Köpfchen', '7 Punkte', 'Stelle den anderen eine leichte Schätz- oder Ratefrage.', NULL),
  ('20', 'Ruheoase', 'Spezial', NULL, NULL, 'Rainbow', 'Pause', 'Durchatmen', 'Hier darf kurz entspannt werden. Perfekt für einen ruhigen Moment zwischen zwei Highlights.', NULL),
  ('21', 'Panoramaweg', 'Straße', '8 Punkte', '6 Punkte', 'Rot', 'Aussicht', '6 Punkte', 'Ein starkes Mittelfeld mit klarer Präsenz.', NULL),
  ('22', 'Sternenplatz', 'Straße', '9 Punkte', '7 Punkte', 'Rot', 'Glanzmoment', '7 Punkte', 'Nenne eine Stärke der Person links von dir.', NULL),
  ('23', 'Pausebank', 'Gefängnis', NULL, NULL, 'Rot', 'Stopp', 'Kurzpause', 'Keine Strafe, nur ein ruhiger Zwischenhalt mit Gelegenheit zum Neustart.', NULL),
  ('24', 'Lichterhof', 'Straße', '10 Punkte', '8 Punkte', 'Rot', 'Atmosphäre', '8 Punkte', 'Ein Premium-Feld für elegante Spielzüge.', NULL),
  ('25', 'Freundschaftsforum', 'Straße', '11 Punkte', '9 Punkte', 'Rot', 'Verbundenheit', '9 Punkte', 'Sage einer Person am Tisch etwas Aufmunterndes oder Nettes.', NULL),
  ('26', 'Genussgarten', 'Straße', '9 Punkte', '7 Punkte', 'Gelb', 'Leichtigkeit', '7 Punkte', 'Das Spieltempo bleibt hoch, die Stimmung entspannt.', NULL),
  ('27', 'Lachterrasse', 'Straße', '10 Punkte', '8 Punkte', 'Gelb', 'Humor', '8 Punkte', 'Teile eine harmlose, lustige Beobachtung aus der Runde.', NULL),
  ('28', 'Ideenwerk', 'Werk', '12 Punkte', '9 Punkte', 'Gelb', 'Werkstatt', '9 Punkte', 'Dieses Feld steht für clevere Einfälle und kreative Vorteile.', NULL),
  ('29', 'Jubelallee', 'Straße', '11 Punkte', '9 Punkte', 'Gelb', 'Momentum', '9 Punkte', 'Hier fühlt sich jeder erfolgreiche Zug direkt größer an.', NULL),
  ('30', 'Fairplay-Zentrale', 'Spezial', NULL, NULL, 'Rainbow', 'Fairplay', 'Ausgleich', 'Eine gute Gelegenheit, die Runde freundlich und ausgeglichen zu halten.', NULL),
  ('31', 'Sommerbühne', 'Straße', '10 Punkte', '8 Punkte', 'Grün', 'Live', '8 Punkte', 'Ein spätes Highlight mit großem Auftritt.', NULL),
  ('32', 'Abenteuerpier', 'Straße', '11 Punkte', '9 Punkte', 'Grün', 'Mut', '9 Punkte', 'Nenne eine Sache, die du dieses Jahr noch ausprobieren möchtest.', NULL),
  ('33', 'Kreativcampus', 'Straße', '12 Punkte', '10 Punkte', 'Grün', 'Ideenfluss', '10 Punkte', 'Hier entstehen neue Impulse für den Endspurt.', NULL),
  ('34', 'Eventhafen', 'Straße', '13 Punkte', '11 Punkte', 'Grün', 'Finalenergie', '11 Punkte', 'Ein starkes Feld kurz vor dem Zielbereich.', NULL),
  ('35', 'Fantasiepark', 'Straße', '14 Punkte', '12 Punkte', 'Grün', 'Traumfeld', '12 Punkte', 'Das Finale wird kreativ: denk dir einen kurzen Teamtitel für eure Runde aus.', NULL),
  ('36', 'Erlebnisbahnhof', 'Bahnhof', '11 Punkte', '8 Punkte', 'Lila', 'Express', '8 Punkte', 'Ein schneller Verbindungspunkt für starke Besitzserien.', NULL),
  ('37', 'Panoramaexpress', 'Bahnhof', '12 Punkte', '9 Punkte', 'Lila', 'Reise', '9 Punkte', 'Perfekt für alle, die das Spielbild gern komplettieren.', NULL),
  ('38', 'Siegerstation', 'Straße', '13 Punkte', '10 Punkte', 'Lila', 'Krönung', '10 Punkte', 'Kurz vor dem Ziel zeigt sich, wer die Runde dominiert.', NULL),
  ('39', 'Servicebeitrag', 'Steuer', NULL, '4 Punkte', 'Lila', 'Abgabe', '4 Punkte', 'Ein neutraler Pflichtstopp, bevor die Schlussgerade beginnt.', NULL),
  ('40', 'Finale der Freude', 'Spezial', NULL, NULL, 'Rainbow', 'Finale', '3 Punkte', 'Die Schlussrunde gehört allen: ein gemeinsamer Jubelmoment zum Abschluss des Kreises.', NULL);
