"""Consultas avanzadas y reportes del catálogo.

Todas las consultas usan JOINs, agregaciones, CTE o funciones de ventana.
Están parametrizadas para evitar inyección SQL.
"""

from __future__ import annotations

from typing import Any, Sequence

from app.db import BaseDatos
from app.errores import ErrorNoEncontrado, ErrorValidacion


class Reportes:
    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    def _consultar(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        return self.bd.consultar(sql, parametros)

    # ------------------------------------------------------------------
    # Resúmenes generales
    # ------------------------------------------------------------------
    def resumen_general(self) -> dict[str, Any]:
        fila = self.bd.consultar_uno(
            """
            SELECT
                (SELECT COUNT(*) FROM guerras)                         AS total_guerras,
                (SELECT COUNT(*) FROM paises)                          AS total_paises,
                (SELECT COUNT(*) FROM participaciones)                 AS participaciones,
                (SELECT COUNT(*) FROM batallas)                        AS total_batallas,
                (SELECT COUNT(*) FROM tratados)                        AS total_tratados,
                (SELECT COUNT(*) FROM guerras WHERE anio_fin IS NULL)  AS guerras_en_curso,
                (SELECT COALESCE(SUM(bajas_totales), 0) FROM guerras)  AS bajas_registradas
            """
        )
        return fila or {}

    def por_siglo(self) -> list[dict[str, Any]]:
        return self._consultar(
            """
            SELECT siglo,
                   total_guerras,
                   bajas_registradas,
                   promedio_bajas,
                   primer_anio
            FROM vw_resumen_siglo
            ORDER BY primer_anio
            """
        )

    def por_region(self) -> list[dict[str, Any]]:
        return self._consultar(
            """
            SELECT id_region,
                   region,
                   continente,
                   total_guerras,
                   bajas_registradas,
                   promedio_bajas
            FROM vw_resumen_region
            ORDER BY total_guerras DESC, region
            """
        )

    def por_tipo(self) -> list[dict[str, Any]]:
        return self._consultar(
            """
            SELECT t.id_tipo,
                   t.nombre AS tipo,
                   COUNT(g.id_guerra) AS total_guerras,
                   COALESCE(SUM(g.bajas_totales), 0) AS bajas_registradas
            FROM tipos_guerra t
            LEFT JOIN guerras g ON g.id_tipo = t.id_tipo
            GROUP BY t.id_tipo, t.nombre
            ORDER BY total_guerras DESC, t.nombre
            """
        )

    # ------------------------------------------------------------------
    # Rankings
    # ------------------------------------------------------------------
    def mas_letales(self, limite: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limite <= 100:
            raise ErrorValidacion("El límite debe estar entre 1 y 100.")
        return self._consultar(
            """
            SELECT id_guerra,
                   nombre,
                   siglo,
                   region,
                   bajas_totales
            FROM vw_guerras_detalle
            WHERE bajas_totales IS NOT NULL
            ORDER BY bajas_totales DESC, nombre
            LIMIT %s
            """,
            (limite,),
        )

    def paises_mas_participaciones(
        self, limite: int = 10
    ) -> list[dict[str, Any]]:
        if not 1 <= limite <= 100:
            raise ErrorValidacion("El límite debe estar entre 1 y 100.")
        return self._consultar(
            """
            SELECT p.id_pais,
                   p.nombre AS pais,
                   COUNT(DISTINCT pa.id_guerra) AS guerras,
                   COALESCE(SUM(pa.bajas), 0) AS bajas_registradas
            FROM paises p
            INNER JOIN participaciones pa ON pa.id_pais = p.id_pais
            GROUP BY p.id_pais, p.nombre
            ORDER BY guerras DESC, bajas_registradas DESC, p.nombre
            LIMIT %s
            """,
            (limite,),
        )

    def paises_mas_victorias(self, limite: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limite <= 100:
            raise ErrorValidacion("El límite debe estar entre 1 y 100.")
        return self._consultar(
            """
            SELECT p.id_pais,
                   p.nombre AS pais,
                   COUNT(DISTINCT pa.id_guerra) AS victorias
            FROM paises p
            INNER JOIN participaciones pa ON pa.id_pais = p.id_pais
            INNER JOIN bandos b
                    ON b.id_bando = pa.id_bando
                   AND b.id_guerra = pa.id_guerra
            WHERE b.resultado = 'Victoria'
            GROUP BY p.id_pais, p.nombre
            ORDER BY victorias DESC, p.nombre
            LIMIT %s
            """,
            (limite,),
        )

    def top_por_region(self, limite: int = 3) -> list[dict[str, Any]]:
        """Top N guerras más letales de cada región (CTE + RANK)."""
        if not 1 <= limite <= 10:
            raise ErrorValidacion("El límite debe estar entre 1 y 10.")
        return self._consultar(
            """
            WITH ranking AS (
                SELECT r.nombre AS region,
                       g.id_guerra,
                       g.nombre AS guerra,
                       g.bajas_totales,
                       RANK() OVER (
                           PARTITION BY g.id_region
                           ORDER BY g.bajas_totales DESC
                       ) AS posicion
                FROM guerras g
                INNER JOIN regiones r ON r.id_region = g.id_region
                WHERE g.bajas_totales IS NOT NULL
            )
            SELECT region, posicion, id_guerra, guerra, bajas_totales
            FROM ranking
            WHERE posicion <= %s
            ORDER BY region, posicion, guerra
            """,
            (limite,),
        )

    def guerras_sin_batallas(self) -> list[dict[str, Any]]:
        return self._consultar(
            """
            SELECT g.id_guerra,
                   g.nombre,
                   g.anio_inicio,
                   g.anio_fin,
                   g.siglo
            FROM guerras g
            LEFT JOIN batallas b ON b.id_guerra = g.id_guerra
            WHERE b.id_batalla IS NULL
            ORDER BY g.anio_inicio
            """
        )

    def guerras_mas_largas(self, limite: int = 10) -> list[dict[str, Any]]:
        if not 1 <= limite <= 100:
            raise ErrorValidacion("El límite debe estar entre 1 y 100.")
        return self._consultar(
            """
            SELECT id_guerra,
                   nombre,
                   anio_inicio,
                   anio_fin,
                   (COALESCE(anio_fin, YEAR(CURDATE())) - anio_inicio) AS duracion_anios
            FROM guerras
            ORDER BY duracion_anios DESC, anio_inicio
            LIMIT %s
            """,
            (limite,),
        )

    # ------------------------------------------------------------------
    # Filtros por bando y por país
    # ------------------------------------------------------------------
    def por_bando(self, texto: str, limite: int = 100) -> list[dict[str, Any]]:
        texto = (texto or "").strip()
        if not texto:
            raise ErrorValidacion("Debe indicar un bando o parte de su nombre.")
        if not 1 <= limite <= 500:
            raise ErrorValidacion("El límite debe estar entre 1 y 500.")

        return self._consultar(
            """
            SELECT DISTINCT
                   g.id_guerra,
                   g.nombre AS guerra,
                   g.anio_inicio,
                   g.anio_fin,
                   b.nombre AS bando,
                   b.resultado AS resultado_bando
            FROM guerras g
            INNER JOIN bandos b ON b.id_guerra = g.id_guerra
            WHERE b.nombre LIKE %s
            ORDER BY g.anio_inicio, g.nombre
            LIMIT %s
            """,
            (f"%{texto}%", limite),
        )

    def por_pais(
        self, id_pais: int, limite: int = 100
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        try:
            id_pais = int(id_pais)
        except (TypeError, ValueError) as exc:
            raise ErrorValidacion("El ID del país debe ser un número entero.") from exc
        if id_pais <= 0:
            raise ErrorValidacion("El ID del país debe ser mayor que 0.")
        if not 1 <= limite <= 500:
            raise ErrorValidacion("El límite debe estar entre 1 y 500.")

        pais = self.bd.consultar_uno(
            "SELECT id_pais, nombre, continente, vigente FROM paises WHERE id_pais = %s",
            (id_pais,),
        )
        if pais is None:
            raise ErrorNoEncontrado(f"No existe un país con ID {id_pais}.")

        filas = self._consultar(
            """
            SELECT g.id_guerra,
                   g.nombre AS guerra,
                   g.anio_inicio,
                   g.anio_fin,
                   g.siglo,
                   b.nombre AS bando,
                   b.resultado AS resultado_bando
            FROM participaciones pa
            INNER JOIN guerras g ON g.id_guerra = pa.id_guerra
            INNER JOIN bandos b
                    ON b.id_bando = pa.id_bando
                   AND b.id_guerra = pa.id_guerra
            WHERE pa.id_pais = %s
            ORDER BY g.anio_inicio, g.nombre
            LIMIT %s
            """,
            (id_pais, limite),
        )
        return pais, filas
