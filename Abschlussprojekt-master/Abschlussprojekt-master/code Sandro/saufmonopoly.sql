-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Erstellungszeit: 10. Jun 2025 um 15:39
-- Server-Version: 10.4.32-MariaDB
-- PHP-Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Datenbank: `saufmonopoly`
--

-- --------------------------------------------------------

--
-- Tabellenstruktur für Tabelle `spielfelder`
--

CREATE TABLE `spielfelder` (
  `feld_id` int(11) NOT NULL,
  `name` varchar(50) NOT NULL,
  `typ` enum('Straße','Bahnhof','Ereignis','Gemeinschaft','Frei Parken','Gefängnis','Los','Steuer','Werk','Spezial') NOT NULL,
  `kaufpreis` varchar(20) DEFAULT NULL,
  `miete` varchar(20) DEFAULT NULL,
  `farbe` varchar(20) DEFAULT NULL,
  `alkohol_typ` enum('Bier','Schnaps','Shot','Wein','Mixgetränk','Kater','Wasser','Joker') NOT NULL,
  `alkohol_menge` varchar(20) NOT NULL,
  `zusatz_regel` varchar(100) DEFAULT NULL,
  `besitzer` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Daten für Tabelle `spielfelder`
--

-- Eckfelder (Special-Felder)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(1, 'Los', 'Los', NULL, NULL, 'Dunkelgrau', 'Wasser', '0', 'Starthilfe: 1 Schluck Bier', NULL),
(10, 'Alkohol-Joker', 'Spezial', NULL, NULL, 'Rainbow', 'Joker', '0', 'Wähle einen beliebigen Alkoholtyp', NULL),
(20, 'Hydrations-Station', 'Spezial', NULL, NULL, 'Rainbow', 'Wasser', '0', 'Trinke Wasser - überspringe nächsten Shot', NULL),
(30, 'Kater-Polizei', 'Spezial', NULL, NULL, 'Rainbow', 'Wasser', '0', 'Wenn du betrunken bist: 1 Runde Pause', NULL),
(40, 'Endspurt', 'Spezial', NULL, NULL, 'Rainbow', 'Shot', '3', 'Letzter Spieler trinkt doppelt', NULL);

-- Felder 2-6: Bier (Braun)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(2, 'Biergasse 1', 'Straße', '2 Schlucke', '1 Schluck', 'Braun', 'Bier', '1 Schluck', NULL, 'Lorenz'),
(3, 'Inndrinks', 'Straße', '3 Schlucke', '2 Schlucke', 'Braun', 'Bier', '2 Schlucke', 'Sie bringen dir ein neues Bier', NULL),
(4, 'HTL Anichstrasse', 'Gemeinschaft', NULL, NULL, 'Braun', 'Bier', '0', 'Würfel bestimmt Menge', NULL),
(5, 'Bierpalast', 'Straße', '5 Schlucke', '3 Schlucke', 'Braun', 'Bier', '3 Schlucke', NULL, NULL),
(6, 'Biergarten', 'Straße', '4 Schlucke', '2 Schlucke', 'Braun', 'Bier', '2 Schlucke', NULL, NULL);

-- Felder 7-9: Wein (Hellblau)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(7, 'Weinberg', 'Straße', '1 Glas', '3 Schlucke', 'Hellblau', 'Wein', '1 Glas', NULL, NULL),
(8, 'Sektempfang', 'Straße', '3 Schlücke', '2 Schlücke', 'Hellblau', 'Wein', '2 Gläser', NULL, NULL),
(9, 'Weinstube', 'Straße', '4 Gläser', '3 Gläser', 'Hellblau', 'Wein', '3 Gläser', NULL, NULL);

-- Felder 11-15: Mixgetränke (Pink)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(11, 'Longdrink-Meile', 'Straße', '6 Schlucke', '5 Schlucke', 'Pink', 'Mixgetränk', '5 Schlucke', NULL, NULL),
(12, 'Cocktail-Straße', 'Straße', '1 Glas', '1 Glas', 'Pink', 'Mixgetränk', '1 Glas', NULL, NULL),
(13, 'Gin-Allee', 'Straße', '5 cl', '2 cl', 'Pink', 'Mixgetränk', '2 cl', NULL, NULL),
(14, 'Whiskey-Platz', 'Straße', '6 cl', '3 cl', 'Pink', 'Mixgetränk', '3 cl', NULL, NULL),
(15, 'Sektbar', 'Straße', '3 Gläser', '2 Gläser', 'Pink', 'Mixgetränk', '2 Gläser', NULL, NULL);

-- Felder 16-19: Schnäpse (Orange)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(16, 'Vodka-Strasse', 'Straße', '3 cl', '2 cl', 'Orange', 'Schnaps', '2 cl', NULL, NULL),
(17, 'Rum-Meile', 'Straße', '4 cl', '3 cl', 'Orange', 'Schnaps', '3 cl', NULL, NULL),
(18, 'Tequila-Kreuzung', 'Straße', '2 Shots', '1 Shot', 'Orange', 'Shot', '1', NULL, NULL),
(19, 'Absinth-Allee', 'Straße', '3 Shots', '2 Shots', 'Orange', 'Shot', '2', NULL, NULL);

-- Felder 21-25: Wein (Rot)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(21, 'Bozner-Platz', 'Straße', '4 Schlücke', '3 Schlücke', 'Rot', 'Wein', '3 Gläser', NULL, NULL),
(22, 'Rotwein-Gasse', 'Straße', '5 Gläser', '4 Gläser', 'Rot', 'Wein', '4 Gläser', NULL, NULL),
(23, 'Gefängnis', 'Gefängnis', NULL, '3 Shots', 'Rot', 'Shot', '3', 'Nachzahlung oder Pause', NULL),
(24, 'Weinhandlung', 'Straße', '6 Gläser', '5 Gläser', 'Rot', 'Wein', '5 Gläser', NULL, NULL),
(25, 'Sektkellerei', 'Straße', '7 Gläser', '6 Gläser', 'Rot', 'Wein', '6 Gläser', NULL, NULL);

-- Felder 26-29: Bier (Gelb)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(26, 'Bierstube', 'Straße', '5 Schlucke', '4 Schlucke', 'Gelb', 'Bier', '4 Schlucke', NULL, NULL),
(27, 'Biergarten', 'Straße', '6 Schlucke', '5 Schlucke', 'Gelb', 'Bier', '5 Schlucke', NULL, NULL),
(28, 'Brauerei', 'Werk', '1 Liter Bier', NULL, 'Gelb', 'Bier', '1 Liter', 'Katerprophylaxe: 2 Runden Schutz', NULL),
(29, 'Bierfest', 'Straße', '7 Schlucke', '6 Schlucke', 'Gelb', 'Bier', '6 Schlucke', NULL, NULL);

-- Felder 31-35: Mixgetränke (Grün)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(31, 'Tiki-Bar', 'Straße', '8 Schlucke', '7 Schlucke', 'Grün', 'Mixgetränk', '7 Schlucke', NULL, NULL),
(32, 'Mojito-Meile', 'Straße', '9 Schlucke', '8 Schlucke', 'Grün', 'Mixgetränk', '8 Schlucke', NULL, NULL),
(33, 'Daiquiri-Diele', 'Straße', '10 Schlucke', '9 Schlucke', 'Grün', 'Mixgetränk', '9 Schlucke', NULL, NULL),
(34, 'Caipirinha-Club', 'Straße', '11 Schlucke', '10 Schlucke', 'Grün', 'Mixgetränk', '10 Schlucke', NULL, NULL),
(35, 'Pina-Colada-Paradies', 'Straße', '12 Schlucke', '11 Schlucke', 'Grün', 'Mixgetränk', '11 Schlucke', NULL, NULL);

-- Felder 36-39: Shots (Lila)
INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(36, 'Vodka-Bahnhof', 'Bahnhof', '6 cl', '3 Shots', 'Lila', 'Shot', '3', NULL, NULL),
(37, 'Sake-Bahnhof', 'Bahnhof', '5 cl', '2 Shots', 'Lila', 'Shot', '2', NULL, NULL),
(38, 'Jägermeister-Station', 'Straße', '4 Shots', '3 Shots', 'Lila', 'Shot', '3', NULL, NULL),
(39, 'Steuer', 'Steuer', NULL, '4 Schlucke', 'Lila', 'Shot', '4', 'An alle verteilen', NULL);

--
-- Indizes der exportierten Tabellen
--

--
-- Indizes für die Tabelle `spielfelder`
--
ALTER TABLE `spielfelder`
  ADD PRIMARY KEY (`feld_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;