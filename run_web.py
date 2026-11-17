#!/usr/bin/env python3
"""Servidor de la interfaz web del Catálogo de Guerras.

Uso:
    python run_web.py
    python run_web.py --puerto 8000
    python run_web.py --host 0.0.0.0 --debug

La conexión a MySQL se configura con las mismas variables de entorno que la
versión de consola: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME.
"""

from __future__ import annotations

import argparse

from app.config import ConfiguracionBD
from app.web import crear_app


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="run_web",
        description="Interfaz web estilo enciclopedia para el catálogo de guerras.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Dirección de escucha (por defecto 127.0.0.1).",
    )
    parser.add_argument(
        "--puerto",
        type=int,
        default=5000,
        help="Puerto HTTP (por defecto 5000).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activa el modo de desarrollo con recarga automática.",
    )
    args = parser.parse_args()

    try:
        configuracion = ConfiguracionBD.desde_entorno()
    except ValueError as exc:
        parser.error(str(exc))

    app = crear_app()
    print("=" * 68)
    print("  Catálogo de Guerras · interfaz web")
    print("=" * 68)
    print(f"  Base de datos : {configuracion.descripcion()}")
    print(f"  Dirección     : http://{args.host}:{args.puerto}/")
    print("  Detén el servidor con Ctrl+C")
    print("=" * 68)
    app.run(host=args.host, port=args.puerto, debug=args.debug)


if __name__ == "__main__":
    main()
