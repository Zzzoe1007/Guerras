#!/usr/bin/env python3
"""Catálogo de Guerras de la Historia.

Punto de entrada de la aplicación de consola. Permite realizar CRUD sobre
la base de datos MySQL y ejecutar reportes avanzados.

Uso:
    python main.py
    python main.py --demo
    python main.py --host localhost --usuario root --contrasena 1234
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from typing import Any, Sequence

from app import ui
from app.config import ConfiguracionBD
from app.db import BaseDatos, ErrorBaseDatos
from app.errores import ErrorCatalogo, ErrorValidacion
from app.reportes import Reportes
from app.repositorio import RepositorioGuerras

SEPARADOR = "=" * 78


def configurar_salida_utf8() -> None:
    """Evita errores de codificación en consolas antiguas de Windows."""
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass


# ----------------------------------------------------------------------------
# Argumentos y configuración
# ----------------------------------------------------------------------------
def crear_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catalogo_guerras",
        description=(
            "Catálogo de guerras de la historia con CRUD en MySQL y reportes."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Variables de entorno:\n"
            "  DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME\n\n"
            "Ejemplos:\n"
            "  python main.py\n"
            "  python main.py --demo\n"
            "  DB_PASSWORD=1234 python main.py\n"
        ),
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Ejecuta una demostración no interactiva de reportes y sale.",
    )
    parser.add_argument("--host", help="Servidor MySQL (por defecto 127.0.0.1).")
    parser.add_argument(
        "--puerto", type=int, help="Puerto MySQL (por defecto 3306)."
    )
    parser.add_argument("--usuario", help="Usuario MySQL (por defecto root).")
    parser.add_argument(
        "--contrasena", help="Contraseña MySQL (mejor use DB_PASSWORD)."
    )
    parser.add_argument(
        "--base-datos", dest="base_datos", help="Nombre de la base de datos."
    )
    return parser


def construir_configuracion(args: argparse.Namespace) -> ConfiguracionBD:
    configuracion = ConfiguracionBD.desde_entorno()
    cambios: dict[str, Any] = {}
    if args.host:
        cambios["host"] = args.host
    if args.puerto is not None:
        cambios["puerto"] = args.puerto
    if args.usuario:
        cambios["usuario"] = args.usuario
    if args.contrasena is not None:
        cambios["contrasena"] = args.contrasena
    if args.base_datos:
        cambios["base_datos"] = args.base_datos
    return replace(configuracion, **cambios)


# ----------------------------------------------------------------------------
# Entradas auxiliares
# ----------------------------------------------------------------------------
def pedir_anio(mensaje: str, *, obligatorio: bool = True) -> int | None:
    while True:
        valor = ui.pedir_entero(
            mensaje,
            minimo=-10000,
            maximo=9999,
            obligatorio=obligatorio,
        )
        if valor is None:
            return None
        if valor == 0:
            print("  ⚠ El año 0 no existe en la cronología histórica.")
            continue
        return valor


def pedir_anio_edicion(
    mensaje: str, actual: int | None, *, permite_limpiar: bool = False
) -> Any:
    while True:
        valor = ui.pedir_entero_edicion(
            mensaje,
            actual,
            minimo=-10000,
            maximo=9999,
            permite_limpiar=permite_limpiar,
        )
        if valor is ui.SIN_CAMBIO or valor is None:
            return valor
        if valor == 0:
            print("  ⚠ El año 0 no existe en la cronología histórica.")
            continue
        return valor


def pedir_id_opcional(
    elementos: Sequence[dict[str, Any]],
    campo_id: str,
    etiqueta: str,
) -> int | None:
    ids_validos = {int(elemento[campo_id]) for elemento in elementos}
    while True:
        valor = ui.pedir_entero(
            f"ID de {etiqueta} (ENTER = todos): ",
            minimo=1,
            obligatorio=False,
        )
        if valor is None:
            return None
        if valor in ids_validos:
            return int(valor)
        print("  ⚠ El ID no existe en el catálogo.")


def pedir_id_edicion(
    mensaje: str, actual: int, ids_validos: set[int]
) -> Any:
    while True:
        valor = ui.pedir_entero_edicion(mensaje, actual, minimo=1)
        if valor is ui.SIN_CAMBIO:
            return valor
        if valor in ids_validos:
            return valor
        print("  ⚠ El ID no existe en el catálogo.")


def elegir_pais(catalogos: dict[str, list[dict[str, Any]]]) -> int:
    texto = ui.pedir_texto("Parte del nombre del país (ej.: Perú): ")
    coincidencias = [
        pais
        for pais in catalogos["paises"]
        if texto.lower() in pais["nombre"].lower()
    ]
    if not coincidencias:
        raise ErrorValidacion(
            f"No se encontraron países que contengan {texto!r}."
        )
    ui.imprimir_tabla(
        ("ID", "País", "Continente"),
        [
            (p["id_pais"], p["nombre"], p["continente"])
            for p in coincidencias
        ],
        max_ancho=35,
    )
    return ui.elegir_id(coincidencias, "id_pais", "nombre", "país")


# ----------------------------------------------------------------------------
# Acciones del CRUD
# ----------------------------------------------------------------------------
def accion_listar(repositorio: RepositorioGuerras) -> None:
    print("\n--- FILTRAR GUERRAS ---")
    print("Deje vacío un campo para no aplicarlo.\n")

    texto = input("Texto (nombre, lugar, resultado, región...): ").strip() or None
    siglo = input("Siglo exacto (ej.: XX, XIX, V a.C.): ").strip() or None

    catalogos = repositorio.catalogos()
    print("\nRegiones disponibles:")
    ui.imprimir_tabla(
        ("ID", "Región", "Continente"),
        [
            (r["id_region"], r["nombre"], r["continente"])
            for r in catalogos["regiones"]
        ],
        max_ancho=30,
    )
    id_region = pedir_id_opcional(
        catalogos["regiones"], "id_region", "región"
    )

    print("\nTipos de guerra disponibles:")
    ui.imprimir_tabla(
        ("ID", "Tipo"),
        [(t["id_tipo"], t["nombre"]) for t in catalogos["tipos"]],
        max_ancho=40,
    )
    id_tipo = pedir_id_opcional(catalogos["tipos"], "id_tipo", "tipo")

    print(
        "\nPeríodo (se muestran guerras activas en algún momento del rango)."
    )
    anio_desde = pedir_anio("Año desde (ENTER = sin límite): ", obligatorio=False)
    anio_hasta = pedir_anio("Año hasta (ENTER = sin límite): ", obligatorio=False)

    limite = ui.pedir_entero(
        "Límite de resultados [100]: ",
        minimo=1,
        maximo=1000,
        obligatorio=False,
    )
    limite = limite or 100

    filas = repositorio.listar(
        texto=texto,
        siglo=siglo,
        id_region=id_region,
        id_tipo=id_tipo,
        anio_desde=anio_desde,
        anio_hasta=anio_hasta,
        limite=limite,
    )

    print(f"\n--- RESULTADOS ({len(filas)}) ---")
    ui.imprimir_tabla(
        (
            "ID",
            "Guerra",
            "Inicio",
            "Fin",
            "Siglo",
            "Tipo",
            "Región",
            "Bajas",
            "Países",
            "Batallas",
        ),
        [
            (
                g["id_guerra"],
                g["nombre"],
                g["anio_inicio"],
                g["anio_fin"] if g["anio_fin"] is not None else "—",
                g["siglo"],
                g["tipo"],
                g["region"],
                ui.numero(g["bajas_totales"]),
                g["num_paises"],
                g["num_batallas"],
            )
            for g in filas
        ],
        max_ancho=38,
    )


def accion_ver_detalle(repositorio: RepositorioGuerras) -> None:
    id_guerra = ui.pedir_entero(
        "\nID de la guerra a consultar: ", minimo=1
    )
    ficha = repositorio.obtener(int(id_guerra))
    ui.mostrar_detalle(ficha)


def accion_crear(repositorio: RepositorioGuerras) -> None:
    print("\n--- REGISTRAR NUEVA GUERRA ---")
    catalogos = repositorio.catalogos()
    ui.mostrar_catalogos(catalogos)

    datos: dict[str, Any] = {}
    datos["nombre"] = ui.pedir_texto("Nombre de la guerra: ", maximo=150)
    datos["anio_inicio"] = pedir_anio(
        "Año de inicio (negativo si es a.C., ej.: -499): "
    )

    while True:
        anio_fin = pedir_anio(
            "Año de fin (ENTER = en curso): ", obligatorio=False
        )
        if anio_fin is None or anio_fin >= datos["anio_inicio"]:
            datos["anio_fin"] = anio_fin
            break
        print("  ⚠ El año de fin no puede ser anterior al de inicio.")

    print(
        "\nFechas exactas (opcional; MySQL solo admite desde el año 1000)."
    )
    datos["fecha_inicio"] = ui.pedir_fecha(
        "Fecha de inicio AAAA-MM-DD (ENTER = desconocida): "
    )
    datos["fecha_fin"] = ui.pedir_fecha(
        "Fecha de fin AAAA-MM-DD (ENTER = desconocida): "
    )

    datos["id_tipo"] = ui.elegir_id(
        catalogos["tipos"], "id_tipo", "nombre", "tipo de guerra"
    )
    datos["id_region"] = ui.elegir_id(
        catalogos["regiones"], "id_region", "nombre", "región"
    )

    datos["lugar"] = ui.pedir_texto(
        "Lugar o teatro de operaciones: ", maximo=180
    )
    datos["resultado"] = (
        input("Resultado (opcional): ").strip() or None
    )
    datos["bajas_totales"] = ui.pedir_entero(
        "Bajas totales estimadas (ENTER = sin dato): ",
        minimo=0,
        obligatorio=False,
    )
    datos["descripcion"] = (
        input("Descripción breve (opcional): ").strip() or None
    )

    print("\n--- RESUMEN ---")
    print(f"  Nombre      : {datos['nombre']}")
    print(
        f"  Período     : {datos['anio_inicio']} - "
        f"{datos['anio_fin'] if datos['anio_fin'] is not None else 'actualidad'}"
    )
    print(f"  Lugar       : {datos['lugar']}")
    print(f"  Bajas       : {ui.numero(datos['bajas_totales'])}")

    if not ui.confirmar("\n¿Guardar esta guerra?", por_defecto=True):
        print("Operación cancelada.")
        return

    nuevo_id = repositorio.crear(datos)
    print(f"\n✔ Guerra creada correctamente con ID {nuevo_id}.")
    print(
        "  Puede agregar bandos, países, batallas y tratados desde "
        "phpMyAdmin o ampliando el repositorio."
    )


def accion_actualizar(repositorio: RepositorioGuerras) -> None:
    print("\n--- ACTUALIZAR GUERRA ---")
    id_guerra = ui.pedir_entero(
        "ID de la guerra a modificar: ", minimo=1
    )
    ficha = repositorio.obtener(int(id_guerra))
    guerra = ficha["guerra"]
    ui.mostrar_detalle(ficha)

    print(
        "\nDeje vacío para mantener el valor actual. "
        "Use '-' para vaciar un campo opcional.\n"
    )
    catalogos = repositorio.catalogos()
    ui.mostrar_catalogos(catalogos)
    ids_tipos = {int(t["id_tipo"]) for t in catalogos["tipos"]}
    ids_regiones = {int(r["id_region"]) for r in catalogos["regiones"]}

    cambios: dict[str, Any] = {}

    valor = ui.pedir_texto_edicion(
        "Nombre", guerra["nombre"], maximo=150
    )
    if valor is not ui.SIN_CAMBIO:
        cambios["nombre"] = valor

    nuevo_inicio = pedir_anio_edicion(
        "Año de inicio", guerra["anio_inicio"]
    )
    if nuevo_inicio is not ui.SIN_CAMBIO:
        cambios["anio_inicio"] = nuevo_inicio

    nuevo_fin = pedir_anio_edicion(
        "Año de fin", guerra["anio_fin"], permite_limpiar=True
    )
    if nuevo_fin is not ui.SIN_CAMBIO:
        cambios["anio_fin"] = nuevo_fin

    inicio_final = (
        nuevo_inicio
        if nuevo_inicio is not ui.SIN_CAMBIO
        else guerra["anio_inicio"]
    )
    fin_final = (
        nuevo_fin if nuevo_fin is not ui.SIN_CAMBIO else guerra["anio_fin"]
    )
    if fin_final is not None and fin_final < inicio_final:
        print(
            "\n⚠ El año de fin no puede ser anterior al año de inicio. "
            "No se guardó ningún cambio."
        )
        return

    fecha_inicio = ui.pedir_fecha_edicion(
        "Fecha de inicio (AAAA-MM-DD)", guerra.get("fecha_inicio")
    )
    if fecha_inicio is not ui.SIN_CAMBIO:
        cambios["fecha_inicio"] = fecha_inicio

    fecha_fin = ui.pedir_fecha_edicion(
        "Fecha de fin (AAAA-MM-DD)", guerra.get("fecha_fin")
    )
    if fecha_fin is not ui.SIN_CAMBIO:
        cambios["fecha_fin"] = fecha_fin

    fi_final = (
        fecha_inicio
        if fecha_inicio is not ui.SIN_CAMBIO
        else guerra.get("fecha_inicio")
    )
    ff_final = (
        fecha_fin
        if fecha_fin is not ui.SIN_CAMBIO
        else guerra.get("fecha_fin")
    )
    if fi_final is not None and ff_final is not None and ff_final < fi_final:
        print(
            "\n⚠ La fecha de fin no puede ser anterior a la fecha de inicio. "
            "No se guardó ningún cambio."
        )
        return

    nuevo_tipo = pedir_id_edicion(
        "ID del tipo de guerra", guerra["id_tipo"], ids_tipos
    )
    if nuevo_tipo is not ui.SIN_CAMBIO:
        cambios["id_tipo"] = nuevo_tipo

    nueva_region = pedir_id_edicion(
        "ID de la región", guerra["id_region"], ids_regiones
    )
    if nueva_region is not ui.SIN_CAMBIO:
        cambios["id_region"] = nueva_region

    valor = ui.pedir_texto_edicion(
        "Lugar", guerra["lugar"], maximo=180
    )
    if valor is not ui.SIN_CAMBIO:
        cambios["lugar"] = valor

    valor = ui.pedir_texto_edicion(
        "Resultado", guerra.get("resultado"),
        maximo=220, permite_limpiar=True,
    )
    if valor is not ui.SIN_CAMBIO:
        cambios["resultado"] = valor

    valor = ui.pedir_entero_edicion(
        "Bajas totales", guerra.get("bajas_totales"),
        minimo=0, permite_limpiar=True,
    )
    if valor is not ui.SIN_CAMBIO:
        cambios["bajas_totales"] = valor

    valor = ui.pedir_texto_edicion(
        "Descripción", guerra.get("descripcion"), permite_limpiar=True
    )
    if valor is not ui.SIN_CAMBIO:
        cambios["descripcion"] = valor

    if not cambios:
        print("\nNo se modificó ningún campo.")
        return

    print("\nCampos a actualizar:")
    for campo, valor in cambios.items():
        print(f"  {campo}: {valor!r}")

    if not ui.confirmar("\n¿Aplicar los cambios?", por_defecto=False):
        print("Operación cancelada.")
        return

    filas = repositorio.actualizar(int(id_guerra), cambios)
    if filas == 0:
        print("\nNo hubo cambios efectivos en la base de datos.")
    else:
        print("\n✔ Guerra actualizada correctamente.")
        ui.mostrar_detalle(repositorio.obtener(int(id_guerra)))


def accion_eliminar(repositorio: RepositorioGuerras) -> None:
    print("\n--- ELIMINAR GUERRA ---")
    id_guerra = ui.pedir_entero(
        "ID de la guerra a eliminar: ", minimo=1
    )
    ficha = repositorio.obtener(int(id_guerra))
    guerra = ficha["guerra"]

    print(f"\n  {guerra['nombre']} ({guerra['anio_inicio']} - "
          f"{guerra['anio_fin'] if guerra['anio_fin'] is not None else 'actualidad'})")
    print(
        f"  Se eliminarán también {len(ficha['participaciones'])} "
        f"participaciones, {len(ficha['batallas'])} batallas y "
        f"{len(ficha['tratados'])} tratados (ON DELETE CASCADE)."
    )

    respuesta = input(
        "\nEscriba ELIMINAR para confirmar la operación: "
    ).strip()
    if respuesta != "ELIMINAR":
        print("Operación cancelada.")
        return

    repositorio.eliminar(int(id_guerra))
    print(f"\n✔ Guerra {id_guerra} eliminada correctamente.")


# ----------------------------------------------------------------------------
# Reportes
# ----------------------------------------------------------------------------
def _encabezado_reporte(titulo: str) -> None:
    print(f"\n{SEPARADOR}\n  {titulo}\n{SEPARADOR}")


def reporte_resumen(reportes: Reportes) -> None:
    _encabezado_reporte("RESUMEN GENERAL DEL CATÁLOGO")
    datos = reportes.resumen_general()
    etiquetas = (
        ("total_guerras", "Guerras registradas"),
        ("total_paises", "Países / entidades"),
        ("participaciones", "Participaciones"),
        ("total_batallas", "Batallas"),
        ("total_tratados", "Tratados"),
        ("guerras_en_curso", "Guerras en curso"),
        ("bajas_registradas", "Bajas registradas"),
    )
    ui.imprimir_tabla(
        ("Métrica", "Valor"),
        [
            (etiqueta, ui.numero(datos.get(clave)))
            for clave, etiqueta in etiquetas
        ],
        max_ancho=45,
    )


def reporte_por_siglo(reportes: Reportes) -> None:
    _encabezado_reporte("GUERRAS POR SIGLO")
    filas = reportes.por_siglo()
    ui.imprimir_tabla(
        ("Siglo", "Guerras", "Bajas registradas", "Promedio", "Primer año"),
        [
            (
                f["siglo"],
                f["total_guerras"],
                ui.numero(f["bajas_registradas"]),
                ui.numero(f["promedio_bajas"]),
                f["primer_anio"],
            )
            for f in filas
        ],
        max_ancho=30,
    )


def reporte_por_region(reportes: Reportes) -> None:
    _encabezado_reporte("GUERRAS POR REGIÓN")
    ui.imprimir_tabla(
        ("Región", "Continente", "Guerras", "Bajas", "Promedio"),
        [
            (
                f["region"],
                f["continente"],
                f["total_guerras"],
                ui.numero(f["bajas_registradas"]),
                ui.numero(f["promedio_bajas"]),
            )
            for f in reportes.por_region()
        ],
        max_ancho=30,
    )


def reporte_por_tipo(reportes: Reportes) -> None:
    _encabezado_reporte("GUERRAS POR TIPO")
    ui.imprimir_tabla(
        ("Tipo", "Guerras", "Bajas registradas"),
        [
            (
                f["tipo"],
                f["total_guerras"],
                ui.numero(f["bajas_registradas"]),
            )
            for f in reportes.por_tipo()
        ],
        max_ancho=40,
    )


def reporte_mas_letales(reportes: Reportes) -> None:
    _encabezado_reporte("TOP 10 GUERRAS CON MÁS BAJAS REGISTRADAS")
    filas = reportes.mas_letales(10)
    ui.imprimir_tabla(
        ("#", "Guerra", "Siglo", "Región", "Bajas"),
        [
            (
                indice,
                f["nombre"],
                f["siglo"],
                f["region"],
                ui.numero(f["bajas_totales"]),
            )
            for indice, f in enumerate(filas, start=1)
        ],
        max_ancho=45,
    )


def reporte_paises_participaciones(reportes: Reportes) -> None:
    _encabezado_reporte("PAÍSES CON MÁS PARTICIPACIONES")
    filas = reportes.paises_mas_participaciones(10)
    ui.imprimir_tabla(
        ("#", "País", "Guerras", "Bajas registradas"),
        [
            (
                indice,
                f["pais"],
                f["guerras"],
                ui.numero(f["bajas_registradas"]),
            )
            for indice, f in enumerate(filas, start=1)
        ],
        max_ancho=40,
    )


def reporte_paises_victorias(reportes: Reportes) -> None:
    _encabezado_reporte("PAÍSES CON MÁS BANDOS VICTORIOSOS")
    filas = reportes.paises_mas_victorias(10)
    ui.imprimir_tabla(
        ("#", "País", "Victorias"),
        [
            (indice, f["pais"], f["victorias"])
            for indice, f in enumerate(filas, start=1)
        ],
        max_ancho=40,
    )


def reporte_por_bando(reportes: Reportes) -> None:
    _encabezado_reporte("BUSCAR GUERRAS POR BANDO")
    texto = ui.pedir_texto(
        "Nombre o parte del bando (ej.: Aliados, Eje, Liga): "
    )
    filas = reportes.por_bando(texto)
    ui.imprimir_tabla(
        ("ID", "Guerra", "Inicio", "Fin", "Bando", "Resultado"),
        [
            (
                f["id_guerra"],
                f["guerra"],
                f["anio_inicio"],
                f["anio_fin"] if f["anio_fin"] is not None else "—",
                f["bando"],
                f["resultado_bando"],
            )
            for f in filas
        ],
        max_ancho=40,
    )


def reporte_por_pais(
    repositorio: RepositorioGuerras, reportes: Reportes
) -> None:
    _encabezado_reporte("GUERRAS DE UN PAÍS")
    catalogos = repositorio.catalogos()
    id_pais = elegir_pais(catalogos)
    pais, filas = reportes.por_pais(id_pais)

    print(
        f"\n  País: {pais['nombre']} ({pais['continente']}) · "
        f"{'vigente' if pais['vigente'] else 'entidad histórica'}"
    )
    ui.imprimir_tabla(
        ("Guerra", "Inicio", "Fin", "Siglo", "Bando", "Resultado"),
        [
            (
                f["guerra"],
                f["anio_inicio"],
                f["anio_fin"] if f["anio_fin"] is not None else "—",
                f["siglo"],
                f["bando"],
                f["resultado_bando"],
            )
            for f in filas
        ],
        max_ancho=40,
    )


def reporte_top_region(reportes: Reportes) -> None:
    _encabezado_reporte("TOP 3 GUERRAS MÁS LETALES POR REGIÓN")
    ui.imprimir_tabla(
        ("Región", "Puesto", "Guerra", "Bajas"),
        [
            (
                f["region"],
                f["posicion"],
                f["guerra"],
                ui.numero(f["bajas_totales"]),
            )
            for f in reportes.top_por_region(3)
        ],
        max_ancho=40,
    )


def reporte_sin_batallas(reportes: Reportes) -> None:
    _encabezado_reporte("GUERRAS SIN BATALLAS REGISTRADAS")
    ui.imprimir_tabla(
        ("ID", "Guerra", "Inicio", "Fin", "Siglo"),
        [
            (
                f["id_guerra"],
                f["nombre"],
                f["anio_inicio"],
                f["anio_fin"] if f["anio_fin"] is not None else "—",
                f["siglo"],
            )
            for f in reportes.guerras_sin_batallas()
        ],
        max_ancho=45,
    )


def reporte_mas_largas(reportes: Reportes) -> None:
    _encabezado_reporte("GUERRAS MÁS LARGAS")
    ui.imprimir_tabla(
        ("#", "Guerra", "Inicio", "Fin", "Años"),
        [
            (
                indice,
                f["nombre"],
                f["anio_inicio"],
                f["anio_fin"] if f["anio_fin"] is not None else "—",
                f["duracion_anios"],
            )
            for indice, f in enumerate(reportes.guerras_mas_largas(10), 1)
        ],
        max_ancho=45,
    )


def menu_reportes(
    repositorio: RepositorioGuerras, reportes: Reportes
) -> None:
    while True:
        print(f"\n{SEPARADOR}")
        print("  REPORTES Y CONSULTAS AVANZADAS")
        print(SEPARADOR)
        print("  1. Resumen general")
        print("  2. Guerras por siglo")
        print("  3. Guerras por región")
        print("  4. Guerras por tipo")
        print("  5. Top 10 guerras más letales")
        print("  6. Países con más participaciones")
        print("  7. Países con más victorias")
        print("  8. Buscar por bando")
        print("  9. Guerras de un país")
        print(" 10. Top 3 más letales por región (función de ventana)")
        print(" 11. Guerras sin batallas registradas")
        print(" 12. Guerras más largas")
        print("  0. Volver al menú principal")

        opcion = ui.pedir_entero("\nOpción: ", minimo=0, maximo=12)
        if opcion == 0:
            return

        try:
            if opcion == 1:
                reporte_resumen(reportes)
            elif opcion == 2:
                reporte_por_siglo(reportes)
            elif opcion == 3:
                reporte_por_region(reportes)
            elif opcion == 4:
                reporte_por_tipo(reportes)
            elif opcion == 5:
                reporte_mas_letales(reportes)
            elif opcion == 6:
                reporte_paises_participaciones(reportes)
            elif opcion == 7:
                reporte_paises_victorias(reportes)
            elif opcion == 8:
                reporte_por_bando(reportes)
            elif opcion == 9:
                reporte_por_pais(repositorio, reportes)
            elif opcion == 10:
                reporte_top_region(reportes)
            elif opcion == 11:
                reporte_sin_batallas(reportes)
            elif opcion == 12:
                reporte_mas_largas(reportes)
        except (ErrorCatalogo, ErrorBaseDatos) as exc:
            print(f"\n[ERROR] {exc}")
        except KeyboardInterrupt:
            print("\nOperación cancelada.")

        ui.pausa()


# ----------------------------------------------------------------------------
# Menú principal y demostración
# ----------------------------------------------------------------------------
def menu_principal(
    repositorio: RepositorioGuerras, reportes: Reportes
) -> None:
    while True:
        print(f"\n{SEPARADOR}")
        print("  CATÁLOGO DE GUERRAS DE LA HISTORIA")
        print("  MySQL + Python · CRUD y reportes")
        print(SEPARADOR)
        print("  1. Listar y filtrar guerras")
        print("  2. Ver ficha completa de una guerra")
        print("  3. Registrar nueva guerra")
        print("  4. Actualizar una guerra")
        print("  5. Eliminar una guerra")
        print("  6. Reportes y consultas avanzadas")
        print("  7. Ayuda / información del proyecto")
        print("  0. Salir")

        opcion = ui.pedir_entero("\nOpción: ", minimo=0, maximo=7)
        if opcion == 0:
            print("\nHasta luego.")
            return

        try:
            if opcion == 1:
                accion_listar(repositorio)
            elif opcion == 2:
                accion_ver_detalle(repositorio)
            elif opcion == 3:
                accion_crear(repositorio)
            elif opcion == 4:
                accion_actualizar(repositorio)
            elif opcion == 5:
                accion_eliminar(repositorio)
            elif opcion == 6:
                menu_reportes(repositorio, reportes)
                continue
            elif opcion == 7:
                mostrar_ayuda()
        except (ErrorCatalogo, ErrorBaseDatos) as exc:
            print(f"\n[ERROR] {exc}")
        except KeyboardInterrupt:
            print("\nOperación cancelada.")

        ui.pausa()


def mostrar_ayuda() -> None:
    print(f"\n{SEPARADOR}\n  AYUDA\n{SEPARADOR}")
    print(
        """
  Este proyecto implementa un catálogo relacional de guerras históricas.

  Base de datos:
    * Motor: MySQL 8.0+ / MariaDB 10.5+
    * Script: sql/catalogo_guerras.sql
    * Tablas: regiones, tipos_guerra, paises, guerras, bandos,
      participaciones, batallas y tratados.
    * Vistas: vw_guerras_detalle, vw_bandos_participantes,
      vw_resumen_siglo y vw_resumen_region.

  Operaciones disponibles:
    * Crear, listar, consultar, actualizar y eliminar guerras.
    * Reportes por siglo, región, tipo, bando y país.
    * Rankings de letalidad y de participación.

  Configuración:
    Variables DB_HOST, DB_PORT, DB_USER, DB_PASSWORD y DB_NAME.
    También puede usar los argumentos --host, --puerto, --usuario,
    --contrasena y --base-datos.

  Ejemplo de ejecución no interactiva:
    python main.py --demo
"""
    )


def ejecutar_demo(repositorio: RepositorioGuerras, reportes: Reportes) -> None:
    print(f"\n{SEPARADOR}")
    print("  DEMOSTRACIÓN NO INTERACTIVA")
    print(SEPARADOR)

    reporte_resumen(reportes)
    reporte_por_siglo(reportes)
    reporte_mas_letales(reportes)
    reporte_paises_participaciones(reportes)
    reporte_top_region(reportes)

    _encabezado_reporte("PRIMERAS 10 GUERRAS DEL CATÁLOGO")
    filas = repositorio.listar(limite=10)
    ui.imprimir_tabla(
        ("ID", "Guerra", "Inicio", "Fin", "Siglo", "Región", "Bajas"),
        [
            (
                g["id_guerra"],
                g["nombre"],
                g["anio_inicio"],
                g["anio_fin"] if g["anio_fin"] is not None else "—",
                g["siglo"],
                g["region"],
                ui.numero(g["bajas_totales"]),
            )
            for g in filas
        ],
        max_ancho=40,
    )

    _encabezado_reporte("FICHA DE EJEMPLO: SEGUNDA GUERRA MUNDIAL")
    ficha = repositorio.obtener(22)
    ui.mostrar_detalle(ficha)

    print("\n✔ Demostración completada: conexión, CRUD y reportes operativos.")


# ----------------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    configurar_salida_utf8()
    parser = crear_parser()
    args = parser.parse_args(argv)

    try:
        configuracion = construir_configuracion(args)
    except ValueError as exc:
        print(f"[ERROR] Configuración inválida: {exc}")
        return 2

    bd = BaseDatos(configuracion)
    repositorio = RepositorioGuerras(bd)
    reportes = Reportes(bd)

    try:
        informacion = bd.probar_conexion()
    except ErrorBaseDatos as exc:
        print(f"\n[ERROR] {exc}")
        print(
            "\nSugerencias:\n"
            "  1. Inicie MySQL (XAMPP/WAMP/Laragon o el servicio del sistema).\n"
            "  2. Importe sql/catalogo_guerras.sql en phpMyAdmin.\n"
            "  3. Revise las variables DB_HOST, DB_PORT, DB_USER, "
            "DB_PASSWORD y DB_NAME.\n"
            "  4. Instale la dependencia con: pip install -r requirements.txt"
        )
        return 1

    print(
        f"\n[OK] Conectado a MySQL {informacion.get('version', '?')} · "
        f"Base de datos: {informacion.get('base_datos', configuracion.base_datos)}"
    )
    print(f"     Servidor: {configuracion.descripcion()}")

    try:
        if args.demo:
            ejecutar_demo(repositorio, reportes)
            return 0
        menu_principal(repositorio, reportes)
    except KeyboardInterrupt:
        print("\n\nPrograma interrumpido por el usuario.")
        return 130
    except (ErrorCatalogo, ErrorBaseDatos) as exc:
        print(f"\n[ERROR] {exc}")
        return 1
    except EOFError:
        print("\nEntrada finalizada.")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
