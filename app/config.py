"""Configuración de la conexión a MySQL.

Los valores se toman de variables de entorno para no dejar credenciales
escritas en el código. También se pueden sobrescribir con argumentos de
línea de comandos (ver main.py).

Variables reconocidas:
    DB_HOST      (por defecto 127.0.0.1)
    DB_PORT      (por defecto 3306)
    DB_USER      (por defecto root)
    DB_PASSWORD  (por defecto vacía, habitual en XAMPP/WAMP)
    DB_NAME      (por defecto catalogo_guerras)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ConfiguracionBD:
    host: str = "127.0.0.1"
    puerto: int = 3306
    usuario: str = "root"
    contrasena: str = ""
    base_datos: str = "catalogo_guerras"
    charset: str = "utf8mb4"

    @classmethod
    def desde_entorno(cls) -> "ConfiguracionBD":
        puerto_texto = os.getenv("DB_PORT", "3306").strip()
        try:
            puerto = int(puerto_texto)
        except ValueError as exc:
            raise ValueError(
                f"DB_PORT debe ser un número entero, se recibió: {puerto_texto!r}"
            ) from exc

        return cls(
            host=os.getenv("DB_HOST", "127.0.0.1").strip() or "127.0.0.1",
            puerto=puerto,
            usuario=os.getenv("DB_USER", "root").strip() or "root",
            contrasena=os.getenv("DB_PASSWORD", ""),
            base_datos=os.getenv("DB_NAME", "catalogo_guerras").strip()
            or "catalogo_guerras",
        )

    def descripcion(self) -> str:
        """Texto seguro para mostrar en mensajes (sin contraseña)."""
        return f"{self.usuario}@{self.host}:{self.puerto}/{self.base_datos}"
