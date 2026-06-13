import os
import logging

from game import app


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.logger.info("server.start host=%s port=%s debug=%s log_level=%s", host, port, debug, os.getenv("LOG_LEVEL", "INFO").upper())
    app.run(debug=debug, host=host, port=port)
