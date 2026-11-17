"""Repositorio de guerras: operaciones CRUD y consultas del catálogo."""

from __future__ import annotations

import datetime as dt
from typing import Any, Sequence

from app.db import BaseDatos, ErrorBaseDatos
from app.errores import (
    ErrorConflicto,
    ErrorNoEncontrado,
    ErrorValidacion,
)

CAMPOS_EDITABLES = (
    "nombre",
    "anio_inicio",
    "anio_fin",
    "fecha_inicio",
    "fecha_fin",
    "id_tipo",
    "id_region",
    "lugar",
    "resultado",
    "bajas_totales",
    "descripcion",
)

CAMPOS_INSERT = (
    "nombre",
    "anio_inicio",
    "anio_fin",
    "fecha_inicio",
    "fecha_fin",
    "siglo",
    "id_tipo",
    "id_region",
    "lugar",
    "resultado",
    "bajas_totales",
    "descripcion",
)

_VALORES_ROMANOS = (
    (1000, "M"),
    (900, "CM"),
    (500, "D"),
    (400, "CD"),
    (100, "C"),
    (90, "XC"),
    (50, "L"),
    (40, "XL"),
    (10, "X"),
    (9, "IX"),
    (5, "V"),
    (4, "IV"),
    (1, "I"),
)


def _a_romano(numero: int) -> str:
    if numero <= 0:
        raise ErrorValidacion("El siglo calculado no es válido.")
    resultado: list[str] = []
    resto = numero
    for valor, simbolo in _VALORES_ROMANOS:
        while resto >= valor:
            resultado.append(simbolo)
            resto -= valor
    return "".join(resultado)


def siglo_desde_anio(anio: int) -> str:
    """Calcula el siglo de un año, con soporte para años a.C.

    Ejemplos: 1914 -> 'XX'; -499 -> 'V a.C.'; -58 -> 'I a.C.'
    """
    if anio == 0:
        raise ErrorValidacion("El año 0 no existe en la cronología histórica.")
    if anio < 0:
        numero = ((-anio - 1) // 100) + 1
        return f"{_a_romano(numero)} a.C."
    numero = ((anio - 1) // 100) + 1
    return _a_romano(numero)


def _texto(
    valor: Any,
    etiqueta: str,
    *,
    obligatorio: bool = True,
    maximo: int | None = None,
) -> str | None:
    texto = "" if valor is None else str(valor).strip()
    if not texto:
        if obligatorio:
            raise ErrorValidacion(f"{etiqueta} es obligatorio.")
        return None
    if maximo is not None and len(texto) > maximo:
        raise ErrorValidacion(
            f"{etiqueta} no puede superar los {maximo} caracteres."
        )
    return texto


def _entero(
    valor: Any,
    etiqueta: str,
    *,
    obligatorio: bool = True,
    minimo: int | None = None,
    maximo: int | None = None,
    permitir_cero: bool = True,
) -> int | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            raise ErrorValidacion(f"{etiqueta} es obligatorio.")
        return None
    if isinstance(valor, bool):
        raise ErrorValidacion(f"{etiqueta} debe ser un número entero.")
    try:
        numero = int(valor.strip()) if isinstance(valor, str) else int(valor)
    except (TypeError, ValueError) as exc:
        raise ErrorValidacion(f"{etiqueta} debe ser un número entero.") from exc

    if not permitir_cero and numero == 0:
        raise ErrorValidacion(f"{etiqueta} no puede ser 0.")
    if minimo is not None and numero < minimo:
        raise ErrorValidacion(f"{etiqueta} debe ser mayor o igual que {minimo}.")
    if maximo is not None and numero > maximo:
        raise ErrorValidacion(f"{etiqueta} debe ser menor o igual que {maximo}.")
    return numero


def _fecha(valor: Any, etiqueta: str) -> dt.date | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    if isinstance(valor, dt.datetime):
        fecha = valor.date()
    elif isinstance(valor, dt.date):
        fecha = valor
    else:
        try:
            fecha = dt.date.fromisoformat(str(valor).strip())
        except ValueError as exc:
            raise ErrorValidacion(
                f"{etiqueta} debe tener el formato AAAA-MM-DD."
            ) from exc

    # MySQL DATE solo admite desde el año 1000. Para guerras antiguas se
    # utilizan únicamente anio_inicio/anio_fin.
    if fecha.year < 1000:
        raise ErrorValidacion(
            f"{etiqueta}: MySQL no admite fechas anteriores al año 1000. "
            "Deje la fecha vacía y use el año histórico."
        )
    return fecha


class RepositorioGuerras:
    """CRUD y consultas sobre la tabla guerras y sus entidades asociadas."""

    def __init__(self, bd: BaseDatos) -> None:
        self.bd = bd

    # ------------------------------------------------------------------
    # Utilidades internas
    # ------------------------------------------------------------------
    @staticmethod
    def _traducir_error(exc: ErrorBaseDatos) -> Exception:
        if exc.errno == 1062:
            return ErrorConflicto(
                "Ya existe una guerra con ese nombre. Use un nombre distinto."
            )
        if exc.errno == 1452:
            return ErrorValidacion(
                "El tipo de guerra, la región o el país indicado no existe."
            )
        if exc.errno == 1451:
            return ErrorConflicto(
                "No se puede eliminar el registro porque tiene datos relacionados."
            )
        if exc.errno in (3819, 4025):
            return ErrorValidacion(
                "Los datos violan una restricción de la base de datos "
                "(por ejemplo, año final anterior al inicial)."
            )
        if exc.errno in (1264, 1406):
            return ErrorValidacion(
                "Uno de los valores es demasiado grande o demasiado largo."
            )
        return exc

    def _consultar(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        try:
            return self.bd.consultar(sql, parametros)
        except ErrorBaseDatos as exc:
            raise self._traducir_error(exc) from exc

    def _uno(
        self, sql: str, parametros: Sequence[Any] | None = None
    ) -> dict[str, Any] | None:
        filas = self._consultar(sql, parametros)
        return filas[0] if filas else None

    def _ejecutar(self, sql: str, parametros: Sequence[Any]) -> tuple[int, int]:
        try:
            return self.bd.ejecutar(sql, parametros)
        except ErrorBaseDatos as exc:
            raise self._traducir_error(exc) from exc

    @staticmethod
    def _patron_busqueda(texto: str) -> str:
        limpio = (
            texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        return f"%{limpio}%"

    @staticmethod
    def _validar_campos(datos: dict[str, Any]) -> None:
        desconocidos = set(datos) - set(CAMPOS_EDITABLES)
        if desconocidos:
            nombres = ", ".join(sorted(desconocidos))
            raise ErrorValidacion(f"Campos no permitidos: {nombres}.")

    def _normalizar_creacion(self, datos: dict[str, Any]) -> dict[str, Any]:
        self._validar_campos(datos)

        nombre = _texto(datos.get("nombre"), "El nombre", maximo=150)
        anio_inicio = _entero(
            datos.get("anio_inicio"),
            "El año de inicio",
            minimo=-10000,
            maximo=9999,
            permitir_cero=False,
        )
        anio_fin = _entero(
            datos.get("anio_fin"),
            "El año de fin",
            obligatorio=False,
            minimo=-10000,
            maximo=9999,
            permitir_cero=False,
        )
        if anio_fin is not None and anio_fin < anio_inicio:
            raise ErrorValidacion(
                "El año de fin no puede ser anterior al año de inicio."
            )

        fecha_inicio = _fecha(datos.get("fecha_inicio"), "La fecha de inicio")
        fecha_fin = _fecha(datos.get("fecha_fin"), "La fecha de fin")
        if (
            fecha_inicio is not None
            and fecha_fin is not None
            and fecha_fin < fecha_inicio
        ):
            raise ErrorValidacion(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )

        id_tipo = _entero(datos.get("id_tipo"), "El tipo de guerra", minimo=1)
        id_region = _entero(datos.get("id_region"), "La región", minimo=1)
        lugar = _texto(datos.get("lugar"), "El lugar", maximo=180)
        resultado = _texto(
            datos.get("resultado"), "El resultado", obligatorio=False, maximo=220
        )
        bajas = _entero(
            datos.get("bajas_totales"),
            "El número de bajas",
            obligatorio=False,
            minimo=0,
            maximo=4294967295,
        )
        descripcion = _texto(
            datos.get("descripcion"), "La descripción", obligatorio=False
        )

        return {
            "nombre": nombre,
            "anio_inicio": anio_inicio,
            "anio_fin": anio_fin,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "siglo": siglo_desde_anio(anio_inicio),
            "id_tipo": id_tipo,
            "id_region": id_region,
            "lugar": lugar,
            "resultado": resultado,
            "bajas_totales": bajas,
            "descripcion": descripcion,
        }

    def _normalizar_actualizacion(
        self, datos: dict[str, Any], actual: dict[str, Any]
    ) -> dict[str, Any]:
        self._validar_campos(datos)
        if not datos:
            return {}

        cambios: dict[str, Any] = {}

        if "nombre" in datos:
            cambios["nombre"] = _texto(
                datos["nombre"], "El nombre", maximo=150
            )

        anio_inicio = actual["anio_inicio"]
        if "anio_inicio" in datos:
            anio_inicio = _entero(
                datos["anio_inicio"],
                "El año de inicio",
                minimo=-10000,
                maximo=9999,
                permitir_cero=False,
            )
            cambios["anio_inicio"] = anio_inicio
            cambios["siglo"] = siglo_desde_anio(anio_inicio)

        anio_fin = actual["anio_fin"]
        if "anio_fin" in datos:
            anio_fin = _entero(
                datos["anio_fin"],
                "El año de fin",
                obligatorio=False,
                minimo=-10000,
                maximo=9999,
                permitir_cero=False,
            )
            cambios["anio_fin"] = anio_fin

        if anio_fin is not None and anio_fin < anio_inicio:
            raise ErrorValidacion(
                "El año de fin no puede ser anterior al año de inicio."
            )

        fecha_inicio = actual.get("fecha_inicio")
        if "fecha_inicio" in datos:
            fecha_inicio = _fecha(datos["fecha_inicio"], "La fecha de inicio")
            cambios["fecha_inicio"] = fecha_inicio

        fecha_fin = actual.get("fecha_fin")
        if "fecha_fin" in datos:
            fecha_fin = _fecha(datos["fecha_fin"], "La fecha de fin")
            cambios["fecha_fin"] = fecha_fin

        if (
            fecha_inicio is not None
            and fecha_fin is not None
            and fecha_fin < fecha_inicio
        ):
            raise ErrorValidacion(
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )

        if "id_tipo" in datos:
            cambios["id_tipo"] = _entero(
                datos["id_tipo"], "El tipo de guerra", minimo=1
            )
        if "id_region" in datos:
            cambios["id_region"] = _entero(
                datos["id_region"], "La región", minimo=1
            )
        if "lugar" in datos:
            cambios["lugar"] = _texto(
                datos["lugar"], "El lugar", maximo=180
            )
        if "resultado" in datos:
            cambios["resultado"] = _texto(
                datos["resultado"],
                "El resultado",
                obligatorio=False,
                maximo=220,
            )
        if "bajas_totales" in datos:
            cambios["bajas_totales"] = _entero(
                datos["bajas_totales"],
                "El número de bajas",
                obligatorio=False,
                minimo=0,
                maximo=4294967295,
            )
        if "descripcion" in datos:
            cambios["descripcion"] = _texto(
                datos["descripcion"], "La descripción", obligatorio=False
            )

        return cambios

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def crear(self, datos: dict[str, Any]) -> int:
        normalizados = self._normalizar_creacion(datos)
        columnas = ", ".join(CAMPOS_INSERT)
        marcadores = ", ".join(["%s"] * len(CAMPOS_INSERT))
        sql = f"INSERT INTO guerras ({columnas}) VALUES ({marcadores})"
        valores = tuple(normalizados[campo] for campo in CAMPOS_INSERT)
        nuevo_id, _ = self._ejecutar(sql, valores)
        return nuevo_id

    def listar(
        self,
        *,
        texto: str | None = None,
        siglo: str | None = None,
        id_region: int | None = None,
        id_tipo: int | None = None,
        anio_desde: int | None = None,
        anio_hasta: int | None = None,
        solo_en_curso: bool = False,
        orden: str = "cronologico",
        limite: int = 100,
    ) -> list[dict[str, Any]]:
        if not 1 <= limite <= 1000:
            raise ErrorValidacion("El límite debe estar entre 1 y 1000.")

        ordenes = {
            "cronologico": "anio_inicio ASC, nombre ASC",
            "reciente": "anio_inicio DESC, nombre ASC",
            "nombre": "nombre ASC",
            "bajas": "bajas_totales IS NULL, bajas_totales DESC, nombre ASC",
            "duracion": (
                "(COALESCE(anio_fin, YEAR(CURDATE())) - anio_inicio) DESC, "
                "anio_inicio ASC"
            ),
        }
        if orden not in ordenes:
            raise ErrorValidacion(
                "El orden debe ser cronologico, reciente, nombre, bajas o duracion."
            )

        condiciones = ["1 = 1"]
        params: list[Any] = []

        if texto and texto.strip():
            patron = self._patron_busqueda(texto.strip())
            condiciones.append(
                "(nombre LIKE %s OR lugar LIKE %s OR resultado LIKE %s "
                "OR descripcion LIKE %s OR tipo LIKE %s OR region LIKE %s)"
            )
            params.extend([patron] * 6)

        if siglo and siglo.strip():
            condiciones.append("siglo = %s")
            params.append(siglo.strip())

        if id_region is not None:
            condiciones.append("id_region = %s")
            params.append(id_region)

        if id_tipo is not None:
            condiciones.append("id_tipo = %s")
            params.append(id_tipo)

        if anio_desde is not None:
            condiciones.append("COALESCE(anio_fin, 9999) >= %s")
            params.append(anio_desde)

        if anio_hasta is not None:
            condiciones.append("anio_inicio <= %s")
            params.append(anio_hasta)

        if solo_en_curso:
            condiciones.append("anio_fin IS NULL")

        sql = (
            "SELECT * FROM vw_guerras_detalle WHERE "
            + " AND ".join(condiciones)
            + f" ORDER BY {ordenes[orden]} LIMIT %s"
        )
        params.append(limite)
        return self._consultar(sql, params)

    def siglos(self) -> list[str]:
        """Siglos presentes en el catálogo, en orden cronológico."""
        filas = self._consultar(
            """
            SELECT siglo, MIN(anio_inicio) AS primer_anio
            FROM guerras
            GROUP BY siglo
            ORDER BY primer_anio
            """
        )
        return [fila["siglo"] for fila in filas]

    def vecinas(self, id_guerra: int) -> dict[str, dict[str, Any] | None]:
        """Devuelve la guerra anterior y la siguiente en orden cronológico."""
        id_guerra = _entero(id_guerra, "El ID de la guerra", minimo=1)
        filas = self._consultar(
            """
            SELECT id_guerra, nombre, anio_inicio, anio_fin
            FROM vw_guerras_detalle
            ORDER BY anio_inicio, nombre
            """
        )
        anterior: dict[str, Any] | None = None
        siguiente: dict[str, Any] | None = None
        for indice, fila in enumerate(filas):
            if fila["id_guerra"] == id_guerra:
                if indice > 0:
                    anterior = filas[indice - 1]
                if indice + 1 < len(filas):
                    siguiente = filas[indice + 1]
                break
        return {"anterior": anterior, "siguiente": siguiente}

    def aleatoria(self) -> dict[str, Any] | None:
        """Una guerra al azar para el enlace «Artículo aleatorio»."""
        return self._uno(
            "SELECT id_guerra, nombre FROM vw_guerras_detalle "
            "ORDER BY RAND() LIMIT 1"
        )

    def buscar_batallas(
        self, texto: str, limite: int = 50
    ) -> list[dict[str, Any]]:
        """Batallas cuyo nombre, lugar o resultado coinciden con el texto."""
        texto = (texto or "").strip()
        if not texto:
            return []
        patron = self._patron_busqueda(texto)
        return self._consultar(
            """
            SELECT b.nombre, b.anio, b.lugar, b.resultado,
                   g.id_guerra, g.nombre AS guerra
            FROM batallas b
            INNER JOIN guerras g ON g.id_guerra = b.id_guerra
            WHERE b.nombre LIKE %s OR b.lugar LIKE %s OR b.resultado LIKE %s
            ORDER BY b.anio, b.nombre
            LIMIT %s
            """,
            (patron, patron, patron, limite),
        )

    def buscar_tratados(
        self, texto: str, limite: int = 50
    ) -> list[dict[str, Any]]:
        """Tratados cuyo nombre o lugar coinciden con el texto."""
        texto = (texto or "").strip()
        if not texto:
            return []
        patron = self._patron_busqueda(texto)
        return self._consultar(
            """
            SELECT t.nombre, t.anio, t.lugar,
                   g.id_guerra, g.nombre AS guerra
            FROM tratados t
            INNER JOIN guerras g ON g.id_guerra = t.id_guerra
            WHERE t.nombre LIKE %s OR t.lugar LIKE %s
            ORDER BY t.anio, t.nombre
            LIMIT %s
            """,
            (patron, patron, limite),
        )

    def obtener(self, id_guerra: int) -> dict[str, Any]:
        id_guerra = _entero(id_guerra, "El ID de la guerra", minimo=1)
        guerra = self._uno(
            "SELECT * FROM vw_guerras_detalle WHERE id_guerra = %s",
            (id_guerra,),
        )
        if guerra is None:
            raise ErrorNoEncontrado(
                f"No existe una guerra con ID {id_guerra}."
            )

        bandos = self._consultar(
            """
            SELECT b.id_bando,
                   b.nombre,
                   b.resultado,
                   b.descripcion,
                   COUNT(pa.id_participacion) AS num_paises
            FROM bandos b
            LEFT JOIN participaciones pa ON pa.id_bando = b.id_bando
            WHERE b.id_guerra = %s
            GROUP BY b.id_bando, b.nombre, b.resultado, b.descripcion
            ORDER BY b.id_bando
            """,
            (id_guerra,),
        )
        participaciones = self._consultar(
            """
            SELECT b.nombre AS bando,
                   b.resultado AS resultado_bando,
                   p.id_pais,
                   p.nombre AS pais,
                   pa.tropas,
                   pa.bajas
            FROM participaciones pa
            INNER JOIN bandos b
                    ON b.id_bando = pa.id_bando
                   AND b.id_guerra = pa.id_guerra
            INNER JOIN paises p ON p.id_pais = pa.id_pais
            WHERE pa.id_guerra = %s
            ORDER BY b.id_bando, p.nombre
            """,
            (id_guerra,),
        )
        batallas = self._consultar(
            """
            SELECT nombre, anio, fecha, lugar, resultado, descripcion
            FROM batallas
            WHERE id_guerra = %s
            ORDER BY anio, nombre
            """,
            (id_guerra,),
        )
        tratados = self._consultar(
            """
            SELECT nombre, anio, lugar, descripcion
            FROM tratados
            WHERE id_guerra = %s
            ORDER BY anio, nombre
            """,
            (id_guerra,),
        )

        return {
            "guerra": guerra,
            "bandos": bandos,
            "participaciones": participaciones,
            "batallas": batallas,
            "tratados": tratados,
        }

    def actualizar(self, id_guerra: int, datos: dict[str, Any]) -> int:
        id_guerra = _entero(id_guerra, "El ID de la guerra", minimo=1)
        actual = self._uno(
            "SELECT * FROM guerras WHERE id_guerra = %s", (id_guerra,)
        )
        if actual is None:
            raise ErrorNoEncontrado(
                f"No existe una guerra con ID {id_guerra}."
            )

        cambios = self._normalizar_actualizacion(datos, actual)
        if not cambios:
            return 0

        asignaciones = ", ".join(f"{campo} = %s" for campo in cambios)
        valores = list(cambios.values())
        valores.append(id_guerra)
        sql = f"UPDATE guerras SET {asignaciones} WHERE id_guerra = %s"
        _, filas = self._ejecutar(sql, tuple(valores))
        return filas

    def eliminar(self, id_guerra: int) -> None:
        id_guerra = _entero(id_guerra, "El ID de la guerra", minimo=1)
        _, filas = self._ejecutar(
            "DELETE FROM guerras WHERE id_guerra = %s", (id_guerra,)
        )
        if filas == 0:
            raise ErrorNoEncontrado(
                f"No existe una guerra con ID {id_guerra}."
            )

    # ------------------------------------------------------------------
    # Catálogos auxiliares
    # ------------------------------------------------------------------
    def catalogos(self) -> dict[str, list[dict[str, Any]]]:
        return {
            "tipos": self._consultar(
                "SELECT id_tipo, nombre FROM tipos_guerra ORDER BY id_tipo"
            ),
            "regiones": self._consultar(
                "SELECT id_region, nombre, continente FROM regiones "
                "ORDER BY id_region"
            ),
            "paises": self._consultar(
                "SELECT id_pais, nombre, continente, vigente FROM paises "
                "ORDER BY nombre"
            ),
        }
