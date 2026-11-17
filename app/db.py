"""Capa de acceso a MySQL.

Usa mysql-connector-python y un *context manager* para garantizar que cada
operación haga COMMIT o ROLLBACK y que el cursor y la conexión se cierren
siempre, incluso cuando ocurre un error.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from app.config import ConfiguracionBD

try:  # Permite mostrar un mensaje amigable si falta la dependencia.
    import mysql.connector
    from mysql.connector import Error as MySQLError

    CONECTOR_DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del entorno
    mysql = None  # type: ignore[assignment]

    class MySQLError(Exception):  # type: ignore[no-redef]
        """Sustituto mínimo cuando mysql-connector-python no está instalado."""

        errno = None
        sqlstate = None
        msg = ""

    CONECTOR_DISPONIBLE = False


MENSAJE_INSTALACION = (
    "Falta la dependencia mysql-connector-python. "
    "Instálela con: pip install -r requirements.txt"
)


class ErrorBaseDatos(Exception):
    """Error controlado de conexión o de ejecución SQL."""

    def __init__(
        self,
        mensaje: str,
        errno: int | None = None,
        sqlstate: str | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.errno = errno
        self.sqlstate = sqlstate


class BaseDatos:
    """Pequeña fachada sobre mysql-connector-python."""

    def __init__(self, configuracion: ConfiguracionBD) -> None:
        self.configuracion = configuracion

    # ------------------------------------------------------------------
    # Conexión y cursores
    # ------------------------------------------------------------------
    def conectar(self):
        if not CONECTOR_DISPONIBLE:
            raise ErrorBaseDatos(MENSAJE_INSTALACION)

        cfg = self.configuracion
        try:
            return mysql.connector.connect(
                host=cfg.host,
                port=cfg.puerto,
                user=cfg.usuario,
                password=cfg.contrasena,
                database=cfg.base_datos,
                charset=cfg.charset,
                use_unicode=True,
                autocommit=False,
                connection_timeout=8,
            )
        except MySQLError as exc:
            raise ErrorBaseDatos(
                self._detallar_error(exc),
                getattr(exc, "errno", None),
                getattr(exc, "sqlstate", None),
            ) from exc

    @contextmanager
    def cursor(self, dictionary: bool = False, commit: bool = True) -> Iterator[Any]:
        conexion = self.conectar()
        cursor = conexion.cursor(dictionary=dictionary, buffered=True)
        try:
            yield cursor
            if commit:
                conexion.commit()
        except Exception:
            conexion.rollback()
            raise
        finally:
            cursor.close()
            conexion.close()

    # ------------------------------------------------------------------
    # Operaciones de alto nivel
    # ------------------------------------------------------------------
    def consultar(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Ejecuta un SELECT y devuelve una lista de diccionarios."""
        try:
            with self.cursor(dictionary=True, commit=False) as cursor:
                cursor.execute(sql, parametros or ())
                return list(cursor.fetchall())
        except MySQLError as exc:
            raise ErrorBaseDatos(
                self._detallar_error(exc),
                getattr(exc, "errno", None),
                getattr(exc, "sqlstate", None),
            ) from exc

    def consultar_uno(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        filas = self.consultar(sql, parametros)
        return filas[0] if filas else None

    def ejecutar(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> tuple[int, int]:
        """Ejecuta INSERT/UPDATE/DELETE y devuelve (lastrowid, rowcount)."""
        try:
            with self.cursor(dictionary=False, commit=True) as cursor:
                cursor.execute(sql, parametros or ())
                return int(cursor.lastrowid or 0), int(cursor.rowcount or 0)
        except MySQLError as exc:
            raise ErrorBaseDatos(
                self._detallar_error(exc),
                getattr(exc, "errno", None),
                getattr(exc, "sqlstate", None),
            ) from exc

    def probar_conexion(self) -> dict[str, Any]:
        """Devuelve la versión del servidor y la base de datos activa."""
        fila = self.consultar_uno(
            "SELECT VERSION() AS version, DATABASE() AS base_datos"
        )
        return fila or {}

    # ------------------------------------------------------------------
    # Mensajes de error amigables
    # ------------------------------------------------------------------
    @staticmethod
    def _detallar_error(exc: MySQLError) -> str:
        errno = getattr(exc, "errno", None)
        detalle = getattr(exc, "msg", None) or str(exc)

        if errno == 1045:
            return (
                "Acceso denegado por MySQL. Revise DB_USER y DB_PASSWORD "
                f"(usuario actual: ver configuración). Detalle: {detalle}"
            )
        if errno == 1049:
            return (
                "La base de datos indicada no existe. Importe primero "
                f"sql/catalogo_guerras.sql. Detalle: {detalle}"
            )
        if errno in (2003, 2005):
            return (
                "No se pudo conectar al servidor MySQL. Compruebe que el "
                "servicio esté iniciado y que DB_HOST/DB_PORT sean correctos. "
                f"Detalle: {detalle}"
            )
        if errno == 1130:
            return (
                "El servidor MySQL no permite conexiones desde este equipo. "
                f"Detalle: {detalle}"
            )
        if errno == 1044:
            return (
                "El usuario de MySQL no tiene permisos sobre esta base de datos. "
                f"Detalle: {detalle}"
            )
        if errno == 1698:
            return (
                "El usuario de MySQL usa autenticación del sistema (auth_socket). "
                "Cree un usuario con contraseña o use sudo/mysql. "
                f"Detalle: {detalle}"
            )
        return f"Error de MySQL: {detalle}"
