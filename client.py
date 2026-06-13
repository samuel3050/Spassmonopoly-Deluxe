import argparse
import logging
import os
import socket
import time
import webbrowser


LOGGER = logging.getLogger("spassmonopoly.client")


def configure_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def get_lan_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip_address = sock.getsockname()[0]
            LOGGER.debug("lan_ip.detected ip=%s", ip_address)
            return ip_address
    except OSError as exc:
        LOGGER.warning("lan_ip.fallback ip=127.0.0.1 error=%s", exc)
        return "127.0.0.1"


def parse_args():
    parser = argparse.ArgumentParser(description="Spassmonopoly Deluxe Lobby-Client starten.")
    parser.add_argument("--host", default=os.getenv("CLIENT_HOST"), help="Server-Host oder IP. Standard: lokale LAN-IP.")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "5000")), help="Server-Port.")
    parser.add_argument("--debug", action="store_true", help="Ausfuehrliche Client-Diagnose aktivieren.")
    parser.add_argument("--no-browser", action="store_true", help="URL nur ausgeben, Browser nicht automatisch oeffnen.")
    return parser.parse_args()


def join_game(args):
    host = args.host or get_lan_ip()
    url = f"http://{host}:{args.port}/lobby"
    LOGGER.info("client.start url=%s host=%s port=%s browser=%s", url, host, args.port, not args.no_browser)

    if args.no_browser:
        print(f"Lobby URL: {url}")
    else:
        opened = webbrowser.open(url)
        LOGGER.info("browser.opened success=%s url=%s", opened, url)
        print(f"Oeffne Browser zur Lobby: {url}")
        print("Browser geoeffnet. Gib deinen Namen in der Lobby ein und warte auf andere Spieler.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("client.stop reason=keyboard_interrupt")
        print("\nVerbindung beendet.")


if __name__ == "__main__":
    parsed_args = parse_args()
    configure_logging(parsed_args.debug)
    join_game(parsed_args)
