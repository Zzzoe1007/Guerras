"""Utilidades de interfaz de consola: tablas, entradas y fichas."""

from __future__ import annotations

import datetime as dt
from typing import Any, Iterable, Sequence

SIN_CAMBIO = object()
ANCHO_MAXIMO = 42


def numero(valor: Any) -> str:
    """Formatea enteros con separador de miles español (70.000.000)."""
    if valor is None:
        return "—"
    try:
        return f"{int(valor):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(valor)


def _celda(valor: Any, ancho: int) -> str:
    if valor is None:
        texto = "—"
    elif isinstance(valor, dt.datetime):
        texto = valor.strftime("%Y-%m-%d %H:%M")
    elif isinstance(valor, dt.date):
        texto = valor.isoformat()
    else:
        texto = str(valor).replace("\n", " ").replace("\r", " ").strip()
    if len(texto) > ancho:
        texto = texto[: max(1, ancho - 1)] + "…"
    return texto


def imprimir_tabla(
    columnas: Sequence[str],
    filas: Iterable[Sequence[Any]],
    *,
    max_ancho: int = ANCHO_MAXIMO,
) -> None:
    """Imprime una tabla ASCII sencilla sin dependencias externas."""
    filas = list(filas)
    if not filas:
        print("  (sin resultados)")
        return

    normalizadas: list[list[Any]] = []
    for fila in filas:
        valores = list(fila)
        if len(valores) < len(columnas):
            valores.extend([None] * (len(columnas) - len(valores)))
        normalizadas.append(valores[: len(columnas)])

    anchos = []
    for indice, encabezado in enumerate(columnas):
        ancho = len(encabezado)
        for fila in normalizadas:
            ancho = max(ancho, len(_celda(fila[indice], max_ancho)))
        anchos.append(min(ancho, max_ancho))

    linea = "+" + "+".join("-" * (ancho + 2) for ancho in anchos) + "+"

    def escribir(valores: Sequence[Any]) -> None:
        celdas = []
        for indice, ancho in enumerate(anchos):
            texto = _celda(valores[indice], ancho)
            celdas.append(f" {texto:<{ancho}} ")
        print("|" + "|".join(celdas) + "|")

    print(linea)
    escribir(list(columnas))
    print(linea)
    for fila in normalizadas:
        escribir(fila)
    print(linea)
    print(f"  Total de filas: {len(normalizadas)}")


def pedir_texto(
    mensaje: str,
    *,
    obligatorio: bool = True,
    maximo: int | None = None,
) -> str:
    while True:
        valor = input(mensaje).strip()
        if not valor:
            if obligatorio:
                print("  ⚠ Este campo es obligatorio.")
                continue
            return ""
        if maximo is not None and len(valor) > maximo:
            print(f"  ⚠ Máximo {maximo} caracteres.")
            continue
        return valor


def pedir_entero(
    mensaje: str,
    *,
    minimo: int | None = None,
    maximo: int | None = None,
    obligatorio: bool = True,
) -> int | None:
    while True:
        valor = input(mensaje).strip()
        if not valor:
            if obligatorio:
                print("  ⚠ Este campo es obligatorio.")
                continue
            return None
        try:
            numero_ingresado = int(valor)
        except ValueError:
            print("  ⚠ Debe escribir un número entero.")
            continue
        if minimo is not None and numero_ingresado < minimo:
            print(f"  ⚠ Debe ser mayor o igual que {minimo}.")
            continue
        if maximo is not None and numero_ingresado > maximo:
            print(f"  ⚠ Debe ser menor o igual que {maximo}.")
            continue
        return numero_ingresado


def pedir_fecha(mensaje: str, *, obligatorio: bool = False) -> dt.date | None:
    while True:
        valor = input(mensaje).strip()
        if not valor:
            if obligatorio:
                print("  ⚠ Este campo es obligatorio.")
                continue
            return None
        try:
            fecha = dt.date.fromisoformat(valor)
        except ValueError:
            print("  ⚠ Formato inválido. Use AAAA-MM-DD (ej.: 1945-09-02).")
            continue
        if fecha.year < 1000:
            print(
                "  ⚠ MySQL no admite fechas anteriores al año 1000. "
                "Deje la fecha vacía y use el año histórico."
            )
            continue
        return fecha


def pedir_entero_edicion(
    mensaje: str,
    actual: int | None,
    *,
    minimo: int | None = None,
    maximo: int | None = None,
    permite_limpiar: bool = False,
) -> Any:
    """Devuelve int, None (limpiar) o SIN_CAMBIO."""
    texto_actual = "sin valor" if actual is None else str(actual)
    ayuda = " [- para vaciar]" if permite_limpiar else ""
    while True:
        valor = input(f"{mensaje} [{texto_actual}]{ayuda}: ").strip()
        if not valor:
            return SIN_CAMBIO
        if permite_limpiar and valor == "-":
            return None
        try:
            numero_ingresado = int(valor)
        except ValueError:
            print("  ⚠ Debe escribir un número entero.")
            continue
        if minimo is not None and numero_ingresado < minimo:
            print(f"  ⚠ Debe ser mayor o igual que {minimo}.")
            continue
        if maximo is not None and numero_ingresado > maximo:
            print(f"  ⚠ Debe ser menor o igual que {maximo}.")
            continue
        return numero_ingresado


def pedir_texto_edicion(
    mensaje: str,
    actual: str | None,
    *,
    maximo: int | None = None,
    permite_limpiar: bool = False,
) -> Any:
    """Devuelve str, None (limpiar) o SIN_CAMBIO."""
    texto_actual = "(sin valor)" if not actual else actual
    ayuda = " [- para vaciar]" if permite_limpiar else ""
    while True:
        valor = input(f"{mensaje} [{texto_actual}]{ayuda}: ").strip()
        if not valor:
            return SIN_CAMBIO
        if permite_limpiar and valor == "-":
            return None
        if maximo is not None and len(valor) > maximo:
            print(f"  ⚠ Máximo {maximo} caracteres.")
            continue
        return valor


def pedir_fecha_edicion(
    mensaje: str, actual: dt.date | None
) -> Any:
    """Devuelve date, None (limpiar) o SIN_CAMBIO."""
    texto_actual = "sin valor" if actual is None else actual.isoformat()
    while True:
        valor = input(f"{mensaje} [{texto_actual}] [- para vaciar]: ").strip()
        if not valor:
            return SIN_CAMBIO
        if valor == "-":
            return None
        try:
            fecha = dt.date.fromisoformat(valor)
        except ValueError:
            print("  ⚠ Formato inválido. Use AAAA-MM-DD.")
            continue
        if fecha.year < 1000:
            print(
                "  ⚠ MySQL no admite fechas anteriores al año 1000. "
                "Use el año histórico."
            )
            continue
        return fecha


def confirmar(mensaje: str, *, por_defecto: bool = False) -> bool:
    opcion = "S/n" if por_defecto else "s/N"
    respuesta = input(f"{mensaje} ({opcion}): ").strip().lower()
    if not respuesta:
        return por_defecto
    return respuesta in {"s", "si", "sí", "y", "yes"}


def pausa(mensaje: str = "Presione ENTER para continuar...") -> None:
    try:
        input(f"\n{mensaje}")
    except EOFError:
        pass


def mostrar_catalogos(catalogos: dict[str, list[dict[str, Any]]]) -> None:
    print("\nTipos de guerra:")
    imprimir_tabla(
        ("ID", "Tipo"),
        [(t["id_tipo"], t["nombre"]) for t in catalogos["tipos"]],
        max_ancho=40,
    )
    print("\nRegiones:")
    imprimir_tabla(
        ("ID", "Región", "Continente"),
        [
            (r["id_region"], r["nombre"], r["continente"])
            for r in catalogos["regiones"]
        ],
        max_ancho=30,
    )


def elegir_id(
    elementos: Sequence[dict[str, Any]],
    campo_id: str,
    campo_nombre: str,
    etiqueta: str,
) -> int:
    ids_validos = {int(elemento[campo_id]) for elemento in elementos}
    while True:
        elegido = pedir_entero(f"ID de {etiqueta}: ", minimo=1)
        if elegido in ids_validos:
            return int(elegido)
        print("  ⚠ El ID no existe en el catálogo mostrado.")


def mostrar_detalle(ficha: dict[str, Any]) -> None:
    guerra = ficha["guerra"]
    separador = "=" * 78

    print(f"\n{separador}")
    print(f"  FICHA DE GUERRA #{guerra['id_guerra']}")
    print(separador)
    print(f"  Nombre      : {guerra['nombre']}")
    fin = guerra["anio_fin"] if guerra["anio_fin"] is not None else "actualidad"
    print(f"  Período     : {guerra['anio_inicio']} - {fin}  ({guerra['siglo']})")

    if guerra.get("fecha_inicio") or guerra.get("fecha_fin"):
        print(
            "  Fechas      : "
            f"{guerra.get('fecha_inicio') or 'desconocida'} → "
            f"{guerra.get('fecha_fin') or 'desconocida'}"
        )
    print(f"  Tipo        : {guerra['tipo']}")
    print(f"  Región      : {guerra['region']} ({guerra['continente']})")
    print(f"  Lugar       : {guerra['lugar']}")
    print(f"  Resultado   : {guerra.get('resultado') or '—'}")
    print(f"  Bajas       : {numero(guerra.get('bajas_totales'))}")
    print(
        "  Registros   : "
        f"{guerra.get('num_paises', 0)} países, "
        f"{guerra.get('num_batallas', 0)} batallas, "
        f"{guerra.get('num_tratados', 0)} tratados"
    )
    print(f"\n  Descripción:\n  {guerra.get('descripcion') or '—'}")

    print("\n  BANDOS")
    imprimir_tabla(
        ("ID", "Bando", "Resultado", "Países"),
        [
            (
                b["id_bando"],
                b["nombre"],
                b.get("resultado"),
                b.get("num_paises", 0),
            )
            for b in ficha["bandos"]
        ],
        max_ancho=45,
    )

    print("\n  PAÍSES PARTICIPANTES")
    imprimir_tabla(
        ("Bando", "País", "Tropas", "Bajas"),
        [
            (
                p["bando"],
                p["pais"],
                numero(p.get("tropas")),
                numero(p.get("bajas")),
            )
            for p in ficha["participaciones"]
        ],
        max_ancho=30,
    )

    print("\n  BATALLAS")
    imprimir_tabla(
        ("Año", "Batalla", "Lugar", "Resultado"),
        [
            (
                b["anio"],
                b["nombre"],
                b.get("lugar"),
                b.get("resultado"),
            )
            for b in ficha["batallas"]
        ],
        max_ancho=40,
    )

    print("\n  TRATADOS / ACUERDOS")
    imprimir_tabla(
        ("Año", "Tratado", "Lugar"),
        [
            (t.get("anio"), t["nombre"], t.get("lugar"))
            for t in ficha["tratados"]
        ],
        max_ancho=45,
    )
    print()
