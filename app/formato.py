"""Funciones de formato compartidas por la interfaz web y los PDF.

Se mantienen en un módulo aparte para que ambas salidas (HTML y PDF) muestren
los años, las cifras y las fechas exactamente igual, sin duplicar lógica.
"""

from __future__ import annotations

import datetime as dt
from typing import Any


def anio_texto(anio: Any) -> str:
    """Devuelve un año legible: 1914, 499 a.C. o un guion si falta."""
    if anio is None or anio == "":
        return "—"
    try:
        numero = int(anio)
    except (TypeError, ValueError):
        return str(anio)
    if numero < 0:
        return f"{abs(numero)} a.C."
    return str(numero)


def rango_anios(inicio: Any, fin: Any) -> str:
    """Rango legible entre dos años, contemplando conflictos en curso."""
    if inicio is None:
        return "—"
    if fin is None:
        return f"{anio_texto(inicio)} – actualidad"
    if inicio == fin:
        return anio_texto(inicio)
    return f"{anio_texto(inicio)} – {anio_texto(fin)}"


def numero(valor: Any) -> str:
    """Número con separador de miles español (1.500.000)."""
    if valor is None or valor == "":
        return "—"
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return str(valor)
    return f"{numero:,}".replace(",", ".")


def fecha_iso(valor: Any) -> str:
    """Formatea una fecha para un <input type="date">."""
    if not valor:
        return ""
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.strftime("%Y-%m-%d")
    return str(valor)[:10]


def fecha_larga(valor: Any) -> str:
    """Fecha en formato dd/mm/aaaa; devuelve un guion si no hay dato."""
    if not valor:
        return "—"
    if isinstance(valor, (dt.date, dt.datetime)):
        return valor.strftime("%d/%m/%Y")
    try:
        return dt.date.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(valor)


def plural(cantidad: Any, singular: str, plural: str) -> str:
    """Elige el singular o el plural según la cantidad."""
    try:
        numero = int(cantidad)
    except (TypeError, ValueError):
        numero = 0
    return singular if numero == 1 else plural


def duracion(anio_inicio: Any, anio_fin: Any) -> str:
    """Duración legible de un conflicto, en años."""
    if anio_inicio is None:
        return "—"
    try:
        inicio = int(anio_inicio)
    except (TypeError, ValueError):
        return "—"
    if anio_fin is None:
        anios = dt.date.today().year - inicio
        return f"{anios} años (en curso)"
    try:
        fin = int(anio_fin)
    except (TypeError, ValueError):
        return "—"
    anios = max(fin - inicio, 0)
    if anios == 0:
        return "menos de un año"
    return f"{anios} {plural(anios, 'año', 'años')}"
