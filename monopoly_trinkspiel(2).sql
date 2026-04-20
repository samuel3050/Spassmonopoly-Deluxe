-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Erstellungszeit: 10. Jun 2025 um 15:08
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
-- Datenbank: `monopoly_trinkspiel`
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
  `alkohol_typ` enum('Bier','Schnaps','Shot','Wein','Mixgetränk','Kater','Wasser') NOT NULL,
  `alkohol_menge` varchar(20) NOT NULL,
  `zusatz_regel` varchar(100) DEFAULT NULL,
  `besitzer` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Daten für Tabelle `spielfelder`
--

INSERT INTO `spielfelder` (`feld_id`, `name`, `typ`, `kaufpreis`, `miete`, `farbe`, `alkohol_typ`, `alkohol_menge`, `zusatz_regel`, `besitzer`) VALUES
(0, 'Los', 'Los', NULL, NULL, NULL, 'Wasser', '0', 'Starthilfe: 1 Schluck Bier', NULL),
(1, 'Biergasse 1', 'Straße', '2 Schlucke', '1 Schluck', 'Gelb', 'Bier', '1 Schluck', NULL, 'Lorenz'),
(2, 'Inndrinks', 'Straße', '3 Schlucke', '2 Schlucke', 'Gelb', 'Bier', '2 Schlucke', 'Sie bringen dir ein neues Bier', NULL),
(3, 'HTL Anichstrasse', 'Gemeinschaft', NULL, NULL, NULL, 'Bier', '0', 'Würfel bestimmt Menge', NULL),
(4, 'Weinberg', 'Straße', '1 Glas', '3 Schlucke', 'Rot', 'Wein', '1 Glas', NULL, NULL),
(5, 'Sektempfang', 'Straße', '3 Schlücke', '2 Schlücke', 'Rot', 'Wein', '2 Gläser', NULL, NULL),
(6, 'Magic', 'Gemeinschaft', NULL, NULL, NULL, '', '0', 'Gönn dir mal eine Pause', NULL),
(7, 'Ereignisfeld', 'Ereignis', NULL, NULL, NULL, 'Shot', '1', 'Karte ziehen: Würfel entscheidet', NULL),
(8, 'Vodka-Strasse', 'Straße', '3 cl', '2 cl', 'Blau', 'Schnaps', '2 cl', NULL, NULL),
(9, 'Rum-Meile', 'Straße', '4 cl', '3 cl', 'Blau', 'Schnaps', '3 cl', NULL, NULL),
(10, 'Tequila-Kreuzung', 'Straße', '2 Shots', '1 Shot', 'Grün', 'Shot', '1', NULL, NULL),
(11, 'Gin-Allee', 'Straße', '5 cl', '2 cl', 'Grün', 'Schnaps', '2 cl', NULL, NULL),
(12, 'Whiskey-Platz', 'Straße', '6 cl', '3 cl', 'Lila', 'Schnaps', '3 cl', NULL, NULL),
(13, 'Frei Parken', 'Frei Parken', NULL, NULL, NULL, 'Wasser', '0', 'Hydrationspause: 1 Runde aussetzen', NULL),
(14, 'Kuppenweg 20', 'Straße', '8 cl', '4 cl', 'Schwarz', 'Schnaps', '4 cl', NULL, NULL),
(15, 'Absinth-Allee', 'Straße', '3 Shots', '2 Shots', 'Schwarz', 'Shot', '2', NULL, NULL),
(16, 'Gemeinschaft', 'Gemeinschaft', NULL, NULL, NULL, 'Mixgetränk', '3 Schlucke', NULL, NULL),
(17, 'Longdrink-Meile', 'Straße', '6 Schlucke', '5 Schlucke', 'Orange', 'Mixgetränk', '5 Schlucke', NULL, NULL),
(18, 'Cocktail-Straße', 'Straße', '1 Glas', '1 Glas', 'Orange', 'Mixgetränk', '1 Glas', NULL, NULL),
(19, 'Wasserwerk', 'Werk', '1 Glas Wasser', NULL, NULL, 'Wasser', '1 Glas', NULL, NULL),
(20, 'Kater-Gasse', 'Straße', 'Volles Glas', 'Mixgetränk ex', 'Rot', 'Kater', 'Alles', NULL, NULL),
(21, 'Hangover-Platz', 'Straße', 'Nachschlag', 'Nachschlag', 'Rot', 'Kater', 'Nachschlag', NULL, NULL),
(22, 'Gefängnis', 'Gefängnis', NULL, '3 Shots', NULL, 'Shot', '3', 'Nachzahlung oder Pause', NULL),
(23, 'Mausefalle', 'Straße', 'Volles Glas', '10 Schlücke', 'Gold', 'Kater', 'Volles Glas', NULL, NULL),
(24, 'Supermarkt', 'Werk', '1 Liter Wasser', NULL, NULL, 'Wasser', '1 Liter', 'Katerprophylaxe: 2 Runden Schutz', NULL),
(25, 'Bierpalast', 'Straße', '5 Schlucke', '3 Schlucke', 'Gelb', 'Bier', '3 Schlucke', NULL, NULL),
(26, 'Sektbar', 'Straße', '3 Gläser', '2 Gläser', 'Rot', 'Wein', '2 Gläser', NULL, NULL),
(27, 'Ereignisfeld', 'Ereignis', NULL, NULL, NULL, 'Shot', '1', NULL, NULL),
(28, 'Whiskey-Brücke', 'Straße', '7 cl', '4 cl', 'Lila', 'Schnaps', '4 cl', NULL, NULL),
(29, 'Sake-Bahnhof', 'Bahnhof', '5 cl', '2 Shots', NULL, 'Schnaps', '2 cl', NULL, NULL),
(30, 'Tiki-Bar', 'Spezial', NULL, '4 Schlücke', NULL, 'Mixgetränk', '4 Schlucke', 'Alle trinken 1 Schluck', NULL),
(31, 'Inndrinks', 'Straße', '6 cl', '4 cl', 'Orange', 'Schnaps', '5 cl', NULL, NULL),
(32, 'Gemeinschaft', 'Gemeinschaft', NULL, NULL, NULL, 'Bier', '2 Schlucke', NULL, NULL),
(33, 'Bozner-Platz', 'Straße', '4 Schlücke', '3 Schlücke', 'Gold', 'Wein', '3 Gläser', NULL, NULL),
(34, 'Ereignisfeld', 'Ereignis', NULL, NULL, NULL, 'Shot', '2', NULL, NULL),
(35, 'Katerklinik', 'Spezial', NULL, NULL, NULL, 'Wasser', '0', 'Heilt 1 Kater-Runde', NULL),
(36, 'Vodka-Bahnhof', 'Bahnhof', '6 cl', '3 Shots', NULL, 'Schnaps', '3 cl', NULL, NULL),
(37, 'Bögen', 'Straße', 'Volles Glas', 'Volles Glas', 'Schwarz', 'Kater', 'Alles', NULL, NULL),
(38, 'Steuer', 'Steuer', NULL, '4 Schlucke', NULL, 'Bier', '4 Schlucke', 'An alle verteilen', NULL),
(39, 'Endspurt', 'Spezial', NULL, NULL, NULL, 'Shot', '3', 'Letzter Spieler trinkt doppelt', NULL);


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
