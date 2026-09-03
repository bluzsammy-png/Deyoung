"""Run the PATI control plane: python -m pati_api (or `pati-server`)."""
from __future__ import annotations

import argparse
import logging


def main() -> None:
    parser = argparse.ArgumentParser(prog="pati-server",
                                     description="Run the PATI control plane (free, local-first)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--public", action="store_true",
                        help="bind 0.0.0.0 (for Cloudflare Tunnel / LAN access)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    import uvicorn
    host = "0.0.0.0" if args.public else args.host
    print(f"Starting PATI control plane on http://{host}:{args.port}")
    print(f"Status page: http://{'127.0.0.1' if host=='127.0.0.1' else '<your-host>'}:{args.port}/")
    uvicorn.run("pati_api.app:app", host=host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
