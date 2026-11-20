"""Interfaz web del Catálogo de Guerras, con estética de enciclopedia.

La aplicación reutiliza la misma base de datos, el repositorio y los reportes
que la versión de consola. No guarda estado propio: cada petición abre las
conexiones que necesita a través de :class:`BaseDatos`.

Para arrancarla::

    python run_web.py

Variables de entorno reconocidas: ``DB_HOST``, ``DB_PORT``, ``DB_USER``,
``DB_PASSWORD``, ``DB_NAME`` y ``SECRET_KEY`` (esta última para firmar la
sesión que protege los formularios).
"""

from __future__ import annotations

import datetime as dt
import io
import os
import secrets
from typing import Any

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException

from app.config import ConfiguracionBD
from app.db import BaseDatos, ErrorBaseDatos
from app.errores import (
    ErrorCatalogo,
    ErrorConflicto,
    ErrorNoEncontrado,
    ErrorValidacion,
)
from app.formato import (
    anio_texto as _anio_texto,
    duracion as _duracion,
    fecha_iso as _fecha_iso,
    fecha_larga as _fecha_larga,
    numero as _numero,
    plural as _plural,
    rango_anios as _rango_anios,
)
from app.pdf import generar_pdf_guerra, nombre_archivo_pdf
from app.reportes import Reportes
from app.repositorio import CAMPOS_EDITABLES, RepositorioGuerras


# ----------------------------------------------------------------------------
# Utilidades de petición
# ----------------------------------------------------------------------------
def _entero_opcional(valor: Any) -> int | None:
    if valor is None or str(valor).strip() == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------
# Fábrica de la aplicación
# ----------------------------------------------------------------------------
def crear_app(configuracion: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    configuracion = dict(configuracion or {})
    app.config.update(
        SECRET_KEY=(
            configuracion.pop("SECRET_KEY", None)
            or os.getenv("SECRET_KEY")
            or "catalogo-guerras-clave-de-desarrollo"
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    app.config.update(configuracion)

    app.jinja_env.filters.update(
        anio=_anio_texto,
        rango_anios=_rango_anios,
        numero=_numero,
        fecha_iso=_fecha_iso,
        fecha_larga=_fecha_larga,
        plural=_plural,
        duracion=_duracion,
    )
    app.jinja_env.globals["csrf_token"] = _csrf_token

    # ------------------------------------------------------------------
    # Contexto de cada petición
    # ------------------------------------------------------------------
    @app.before_request
    def _preparar_peticion() -> None:
        try:
            g.config = ConfiguracionBD.desde_entorno()
        except ValueError as exc:
            raise ErrorBaseDatos(str(exc)) from exc
        g.bd = BaseDatos(g.config)
        g.repo = RepositorioGuerras(g.bd)
        g.reportes = Reportes(g.bd)

    @app.context_processor
    def _contexto_comun() -> dict[str, Any]:
        datos: dict[str, Any] = {
            "nav_total": 0,
            "nav_paises": 0,
            "nav_batallas": 0,
            "nav_tratados": 0,
            "nav_siglos": [],
            "anio_actual": dt.date.today().year,
        }
        try:
            repo = getattr(g, "repo", None)
            if repo is not None:
                resumen = repo.bd.consultar_uno(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM guerras)  AS guerras,
                        (SELECT COUNT(*) FROM paises)   AS paises,
                        (SELECT COUNT(*) FROM batallas) AS batallas,
                        (SELECT COUNT(*) FROM tratados) AS tratados
                    """
                ) or {}
                datos.update(
                    nav_total=resumen.get("guerras", 0),
                    nav_paises=resumen.get("paises", 0),
                    nav_batallas=resumen.get("batallas", 0),
                    nav_tratados=resumen.get("tratados", 0),
                    nav_siglos=repo.siglos(),
                )
        except Exception:  # La cabecera nunca debe romper una página.
            pass
        return datos

    # ------------------------------------------------------------------
    # Portada
    # ------------------------------------------------------------------
    @app.route("/")
    def portada():
        resumen = g.reportes.resumen_general()
        letales = g.reportes.mas_letales(6)
        destacada = None
        if letales:
            try:
                datos = g.repo.listar(
                    texto=letales[0]["nombre"], limite=1
                )
                if datos:
                    destacada = g.repo.obtener(datos[0]["id_guerra"])
            except ErrorCatalogo:
                destacada = None
        return render_template(
            "index.html",
            resumen=resumen,
            letales=letales,
            destacada=destacada,
            recientes=g.repo.listar(limite=6, orden="reciente"),
            por_siglo=g.reportes.por_siglo(),
            por_region=g.reportes.por_region(),
            por_tipo=g.reportes.por_tipo(),
            ejemplo=g.repo.listar(limite=4),
        )

    # ------------------------------------------------------------------
    # Búsqueda y listados
    # ------------------------------------------------------------------
    @app.route("/buscar")
    def buscar():
        consulta = (request.args.get("q") or "").strip()
        guerras: list[dict[str, Any]] = []
        paises: list[dict[str, Any]] = []
        batallas: list[dict[str, Any]] = []
        tratados: list[dict[str, Any]] = []
        bandos: list[dict[str, Any]] = []

        if consulta:
            guerras = g.repo.listar(texto=consulta, limite=200)
            paises = [
                pais
                for pais in g.repo.catalogos()["paises"]
                if consulta.lower() in pais["nombre"].lower()
            ][:30]
            batallas = g.repo.buscar_batallas(consulta, limite=30)
            tratados = g.repo.buscar_tratados(consulta, limite=30)
            try:
                bandos = g.reportes.por_bando(consulta, limite=30)
            except ErrorValidacion:
                bandos = []

        total = (
            len(guerras) + len(paises) + len(batallas) + len(tratados) + len(bandos)
        )
        return render_template(
            "buscar.html",
            consulta=consulta,
            guerras=guerras,
            paises=paises,
            batallas=batallas,
            tratados=tratados,
            bandos=bandos,
            total=total,
        )

    @app.route("/guerras")
    def guerras():
        consulta = (request.args.get("q") or "").strip()
        siglo = (request.args.get("siglo") or "").strip()
        id_region = _entero_opcional(request.args.get("region"))
        id_tipo = _entero_opcional(request.args.get("tipo"))
        anio_desde = _entero_opcional(request.args.get("desde"))
        anio_hasta = _entero_opcional(request.args.get("hasta"))
        solo_en_curso = request.args.get("curso") == "1"
        orden = (request.args.get("orden") or "cronologico").strip()
        if orden not in {"cronologico", "reciente", "nombre", "bajas", "duracion"}:
            orden = "cronologico"

        filas = g.repo.listar(
            texto=consulta or None,
            siglo=siglo or None,
            id_region=id_region,
            id_tipo=id_tipo,
            anio_desde=anio_desde,
            anio_hasta=anio_hasta,
            solo_en_curso=solo_en_curso,
            orden=orden,
            limite=1000,
        )
        return render_template(
            "guerras.html",
            guerras=filas,
            catalogos=g.repo.catalogos(),
            siglos=g.repo.siglos(),
            filtros={
                "q": consulta,
                "siglo": siglo,
                "region": id_region,
                "tipo": id_tipo,
                "desde": request.args.get("desde", ""),
                "hasta": request.args.get("hasta", ""),
                "curso": solo_en_curso,
                "orden": orden,
            },
        )

    # ------------------------------------------------------------------
    # Artículo
    # ------------------------------------------------------------------
    @app.route("/guerra/<int:id_guerra>")
    def guerra(id_guerra: int):
        datos = g.repo.obtener(id_guerra)
        vecinas = g.repo.vecinas(id_guerra)

        total_tropas = sum(
            p.get("tropas") or 0 for p in datos["participaciones"]
        )
        total_bajas = sum(
            p.get("bajas") or 0 for p in datos["participaciones"]
        )
        if not total_bajas:
            total_bajas = datos["guerra"].get("bajas_totales")
        total_tropas = total_tropas or None
        total_bajas = total_bajas or None

        cronologia: list[dict[str, Any]] = []
        for batalla in datos["batallas"]:
            cronologia.append(
                {
                    "anio": batalla.get("anio"),
                    "tipo": "Batalla",
                    "titulo": batalla.get("nombre"),
                    "lugar": batalla.get("lugar"),
                    "detalle": batalla.get("resultado"),
                }
            )
        for tratado in datos["tratados"]:
            cronologia.append(
                {
                    "anio": tratado.get("anio"),
                    "tipo": "Tratado",
                    "titulo": tratado.get("nombre"),
                    "lugar": tratado.get("lugar"),
                    "detalle": None,
                }
            )
        cronologia.sort(key=lambda fila: (fila["anio"] is None, fila["anio"] or 0))

        return render_template(
            "guerra.html",
            **datos,
            vecinas=vecinas,
            total_tropas=total_tropas,
            total_bajas=total_bajas,
            cronologia=cronologia,
        )

    @app.route("/guerra/<int:id_guerra>/pdf")
    def guerra_pdf(id_guerra: int):
        """Descarga la ficha completa de la guerra en formato PDF."""
        datos = g.repo.obtener(id_guerra)
        contenido = generar_pdf_guerra(datos)
        respuesta = send_file(
            io.BytesIO(contenido),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=nombre_archivo_pdf(datos["guerra"]),
            max_age=0,
        )
        respuesta.headers["Cache-Control"] = "no-store"
        return respuesta

    @app.route("/aleatoria")
    def aleatoria():
        fila = g.repo.aleatoria()
        if not fila:
            flash("Todavía no hay guerras en el catálogo.", "aviso")
            return redirect(url_for("portada"))
        return redirect(url_for("guerra", id_guerra=fila["id_guerra"]))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @app.route("/guerra/nueva", methods=["GET", "POST"])
    def nueva():
        catalogos = g.repo.catalogos()
        if request.method == "POST":
            _validar_csrf()
            datos = _datos_formulario()
            try:
                nuevo_id = g.repo.crear(datos)
            except ErrorCatalogo as exc:
                flash(str(exc), "error")
                return render_template(
                    "formulario.html",
                    modo="crear",
                    datos=datos,
                    catalogos=catalogos,
                ), 400
            flash("La guerra se ha añadido al catálogo.", "exito")
            return redirect(url_for("guerra", id_guerra=nuevo_id))

        return render_template(
            "formulario.html",
            modo="crear",
            datos={},
            catalogos=catalogos,
        )

    @app.route("/guerra/<int:id_guerra>/editar", methods=["GET", "POST"])
    def editar(id_guerra: int):
        datos_guerra = g.repo.obtener(id_guerra)["guerra"]
        catalogos = g.repo.catalogos()
        if request.method == "POST":
            _validar_csrf()
            datos = _datos_formulario()
            try:
                g.repo.actualizar(id_guerra, datos)
            except ErrorCatalogo as exc:
                flash(str(exc), "error")
                formulario = dict(datos_guerra)
                formulario.update(datos)
                return render_template(
                    "formulario.html",
                    modo="editar",
                    datos=formulario,
                    catalogos=catalogos,
                    guerra=datos_guerra,
                ), 400
            flash("Los cambios se han guardado correctamente.", "exito")
            return redirect(url_for("guerra", id_guerra=id_guerra))

        return render_template(
            "formulario.html",
            modo="editar",
            datos=datos_guerra,
            catalogos=catalogos,
            guerra=datos_guerra,
        )

    @app.route("/guerra/<int:id_guerra>/eliminar", methods=["GET", "POST"])
    def eliminar(id_guerra: int):
        datos_guerra = g.repo.obtener(id_guerra)["guerra"]
        if request.method == "POST":
            _validar_csrf()
            if request.form.get("confirmar") != "si":
                flash("Debes confirmar la eliminación del artículo.", "aviso")
                return redirect(url_for("eliminar", id_guerra=id_guerra))
            try:
                g.repo.eliminar(id_guerra)
            except ErrorConflicto as exc:
                flash(str(exc), "error")
                return redirect(url_for("guerra", id_guerra=id_guerra))
            flash(
                f"«{datos_guerra['nombre']}» se ha eliminado del catálogo.",
                "exito",
            )
            return redirect(url_for("portada"))

        return render_template("eliminar.html", guerra=datos_guerra)

    # ------------------------------------------------------------------
    # Reportes y páginas auxiliares
    # ------------------------------------------------------------------
    @app.route("/reportes")
    def reportes():
        return render_template(
            "reportes.html",
            resumen=g.reportes.resumen_general(),
            siglos=g.reportes.por_siglo(),
            regiones=g.reportes.por_region(),
            tipos=g.reportes.por_tipo(),
            letales=g.reportes.mas_letales(10),
            largas=g.reportes.guerras_mas_largas(10),
            paises=g.reportes.paises_mas_participaciones(10),
            victorias=g.reportes.paises_mas_victorias(10),
            top_region=g.reportes.top_por_region(3),
            sin_batallas=g.reportes.guerras_sin_batallas(),
        )

    @app.route("/pais/<int:id_pais>")
    def pais(id_pais: int):
        datos_pais, participaciones = g.reportes.por_pais(id_pais, limite=500)
        return render_template(
            "pais.html", pais=datos_pais, participaciones=participaciones
        )

    @app.route("/ayuda")
    def ayuda():
        return render_template("ayuda.html")

    # ------------------------------------------------------------------
    # Errores
    # ------------------------------------------------------------------
    @app.errorhandler(ErrorNoEncontrado)
    def _error_no_encontrado(exc: ErrorNoEncontrado):
        return (
            render_template(
                "error.html",
                codigo=404,
                titulo="Artículo no encontrado",
                mensaje=str(exc),
            ),
            404,
        )

    @app.errorhandler(ErrorValidacion)
    def _error_validacion(exc: ErrorValidacion):
        return (
            render_template(
                "error.html",
                codigo=400,
                titulo="Datos no válidos",
                mensaje=str(exc),
            ),
            400,
        )

    @app.errorhandler(ErrorConflicto)
    def _error_conflicto(exc: ErrorConflicto):
        return (
            render_template(
                "error.html",
                codigo=409,
                titulo="Operación en conflicto",
                mensaje=str(exc),
            ),
            409,
        )

    @app.errorhandler(ErrorCatalogo)
    def _error_catalogo(exc: ErrorCatalogo):
        return (
            render_template(
                "error.html",
                codigo=400,
                titulo="No se pudo completar la operación",
                mensaje=str(exc),
            ),
            400,
        )

    @app.errorhandler(ErrorBaseDatos)
    def _error_base_datos(exc: ErrorBaseDatos):
        return (
            render_template(
                "error.html",
                codigo=503,
                titulo="Sin conexión con la base de datos",
                mensaje=str(exc),
                mostrar_ayuda_bd=True,
            ),
            503,
        )

    @app.errorhandler(404)
    def _pagina_no_encontrada(exc: HTTPException):
        return (
            render_template(
                "404.html",
                codigo=404,
                titulo="Página no encontrada",
                mensaje="La dirección solicitada no existe en el catálogo.",
            ),
            404,
        )

    @app.errorhandler(500)
    def _error_interno(exc: Exception):
        app.logger.exception("Error interno en la interfaz web")
        return (
            render_template(
                "error.html",
                codigo=500,
                titulo="Error interno",
                mensaje=(
                    "Se produjo un error inesperado. Revisa la consola donde "
                    "se ejecuta la aplicación para ver el detalle."
                ),
            ),
            500,
        )

    return app


# ----------------------------------------------------------------------------
# Formularios y CSRF
# ----------------------------------------------------------------------------
def _csrf_token() -> str:
    token = session.get("_csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf"] = token
    return token


def _validar_csrf() -> None:
    esperado = session.get("_csrf")
    recibido = request.form.get("csrf_token", "")
    if not esperado or not secrets.compare_digest(esperado, recibido):
        raise ErrorValidacion(
            "El formulario ha caducado o no es válido. Vuelve a cargarlo e "
            "inténtalo de nuevo."
        )


def _datos_formulario() -> dict[str, Any]:
    return {campo: request.form.get(campo) for campo in CAMPOS_EDITABLES}
