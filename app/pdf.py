"""Generación de fichas PDF de las guerras del catálogo.

Usa ReportLab para componer un documento A4 con la misma información que el
artículo web: ficha de datos, contexto histórico, bandos, países, batallas,
tratados y cronología. Las fuentes DejaVu se cargan desde el sistema para que
los acentos, las comillas españolas y los guiones largos se impriman bien.
"""

from __future__ import annotations

import datetime as dt
import io
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Sequence
from xml.sax.saxutils import escape

from app.errores import ErrorCatalogo
from app.formato import anio_texto, duracion, fecha_larga, numero, rango_anios

try:  # La web puede arrancar aunque falte ReportLab; solo falla al pedir un PDF.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        BaseDocTemplate,
        CondPageBreak,
        Frame,
        HRFlowable,
        KeepTogether,
        PageTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del entorno
    REPORTLAB_DISPONIBLE = False

MENSAJE_SIN_REPORTLAB = (
    "La descarga en PDF necesita la librería ReportLab. "
    "Instálala con: pip install -r requirements.txt"
)

AZUL = "#3366cc"
AZUL_OSCURO = "#2a4b8d"
GRIS = "#54595d"
GRIS_TENUE = "#72777d"
BORDE = "#c8ccd1"
FONDO_SUAVE = "#f8f9fa"

_RUTAS_FUENTES = {
    "sans": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ],
    "sans_negrita": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ],
    "sans_cursiva": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Oblique.ttf",
    ],
    "sans_negrita_cursiva": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-BoldOblique.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif.ttf",
    ],
    "serif_negrita": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf",
    ],
}


@dataclass(frozen=True)
class _Fuentes:
    cuerpo: str
    negrita: str
    cursiva: str
    negrita_cursiva: str
    titulo: str
    titulo_negrita: str
    incrustadas: bool


_FUENTES: _Fuentes | None = None


def _registrar_fuentes() -> _Fuentes:
    """Registra DejaVu si está disponible; si no, usa las fuentes de ReportLab."""
    global _FUENTES
    if _FUENTES is not None:
        return _FUENTES

    def _primera(rutas: Sequence[str]) -> str | None:
        for ruta in rutas:
            try:
                with open(ruta, "rb"):
                    return ruta
            except OSError:
                continue
        return None

    disponibles = {clave: _primera(rutas) for clave, rutas in _RUTAS_FUENTES.items()}
    if all(disponibles.values()):
        try:
            pdfmetrics.registerFont(TTFont("BellumSans", disponibles["sans"]))
            pdfmetrics.registerFont(
                TTFont("BellumSans-Bold", disponibles["sans_negrita"])
            )
            pdfmetrics.registerFont(
                TTFont("BellumSans-Italic", disponibles["sans_cursiva"])
            )
            pdfmetrics.registerFont(
                TTFont("BellumSans-BoldItalic", disponibles["sans_negrita_cursiva"])
            )
            pdfmetrics.registerFont(TTFont("BellumSerif", disponibles["serif"]))
            pdfmetrics.registerFont(
                TTFont("BellumSerif-Bold", disponibles["serif_negrita"])
            )
            pdfmetrics.registerFontFamily(
                "BellumSans",
                normal="BellumSans",
                bold="BellumSans-Bold",
                italic="BellumSans-Italic",
                boldItalic="BellumSans-BoldItalic",
            )
            pdfmetrics.registerFontFamily(
                "BellumSerif",
                normal="BellumSerif",
                bold="BellumSerif-Bold",
                italic="BellumSerif",
                boldItalic="BellumSerif-Bold",
            )
            _FUENTES = _Fuentes(
                cuerpo="BellumSans",
                negrita="BellumSans-Bold",
                cursiva="BellumSans-Italic",
                negrita_cursiva="BellumSans-BoldItalic",
                titulo="BellumSerif",
                titulo_negrita="BellumSerif-Bold",
                incrustadas=True,
            )
            return _FUENTES
        except Exception:  # Fuente dañada: se continúa con las estándar.
            pass

    _FUENTES = _Fuentes(
        cuerpo="Helvetica",
        negrita="Helvetica-Bold",
        cursiva="Helvetica-Oblique",
        negrita_cursiva="Helvetica-BoldOblique",
        titulo="Times-Roman",
        titulo_negrita="Times-Bold",
        incrustadas=False,
    )
    return _FUENTES


# ----------------------------------------------------------------------------
# Estilos
# ----------------------------------------------------------------------------
def _estilos(fuentes: _Fuentes) -> dict[str, ParagraphStyle]:
    return {
        "marca": ParagraphStyle(
            "marca",
            fontName=fuentes.negrita,
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
        ),
        "titulo": ParagraphStyle(
            "titulo",
            fontName=fuentes.titulo_negrita,
            fontSize=21,
            leading=24,
            textColor=colors.HexColor("#1b1d20"),
            spaceAfter=3,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            fontName=fuentes.cuerpo,
            fontSize=9.2,
            leading=12,
            textColor=colors.HexColor(GRIS),
            spaceAfter=2,
        ),
        "seccion": ParagraphStyle(
            "seccion",
            fontName=fuentes.titulo_negrita,
            fontSize=13,
            leading=16,
            textColor=colors.HexColor(AZUL_OSCURO),
            spaceBefore=4,
            spaceAfter=2,
        ),
        "bando": ParagraphStyle(
            "bando",
            fontName=fuentes.negrita,
            fontSize=10,
            leading=12.5,
            textColor=colors.HexColor("#1b1d20"),
            spaceBefore=5,
            spaceAfter=2,
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo",
            fontName=fuentes.cuerpo,
            fontSize=9.2,
            leading=13.6,
            alignment=4,  # justificado
            textColor=colors.HexColor("#202122"),
            spaceAfter=5,
        ),
        "aviso": ParagraphStyle(
            "aviso",
            fontName=fuentes.cursiva,
            fontSize=8.8,
            leading=12.5,
            textColor=colors.HexColor(GRIS),
            backColor=colors.HexColor(FONDO_SUAVE),
            borderColor=colors.HexColor(BORDE),
            borderWidth=0.5,
            borderPadding=5,
            spaceBefore=2,
            spaceAfter=4,
        ),
        "celda": ParagraphStyle(
            "celda",
            fontName=fuentes.cuerpo,
            fontSize=8.2,
            leading=10.6,
            textColor=colors.HexColor("#202122"),
        ),
        "celda_pequena": ParagraphStyle(
            "celda_pequena",
            fontName=fuentes.cuerpo,
            fontSize=7.4,
            leading=9.4,
            textColor=colors.HexColor(GRIS),
        ),
        "cabecera": ParagraphStyle(
            "cabecera",
            fontName=fuentes.negrita,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#202122"),
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta",
            fontName=fuentes.negrita,
            fontSize=7.8,
            leading=10,
            textColor=colors.HexColor(GRIS),
        ),
        "pie": ParagraphStyle(
            "pie",
            fontName=fuentes.cursiva,
            fontSize=7.6,
            leading=10,
            textColor=colors.HexColor(GRIS_TENUE),
            spaceBefore=6,
        ),
    }


# ----------------------------------------------------------------------------
# Utilidades de contenido
# ----------------------------------------------------------------------------
def _texto(valor: Any, defecto: str = "—") -> str:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return defecto
    return str(valor)


def _parrafos(texto: Any, estilo: ParagraphStyle) -> list[Paragraph]:
    if not texto:
        return []
    bloques = [b.strip() for b in re.split(r"\n\s*\n", str(texto)) if b.strip()]
    return [
        Paragraph(escape(b).replace("\n", "<br/>"), estilo) for b in bloques
    ]


def _tabla(
    cabeceras: Sequence[str],
    filas: Sequence[Sequence[Any]],
    anchos: Sequence[float],
    estilos: dict[str, ParagraphStyle],
) -> Table:
    """Construye una tabla con cabecera repetida y celdas que ajustan texto."""
    datos: list[list[Any]] = [
        [
            Paragraph(escape(cabecera), estilos["cabecera"])
            for cabecera in cabeceras
        ]
    ]
    for fila in filas:
        celdas: list[Any] = []
        for valor in fila:
            if isinstance(valor, Paragraph):
                celdas.append(valor)
                continue
            celdas.append(
                Paragraph(escape(_texto(valor)), estilos["celda"])
            )
        datos.append(celdas)

    tabla = Table(datos, colWidths=list(anchos), repeatRows=1, hAlign="LEFT")
    orden = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6e9ed")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(BORDE)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfc")]),
    ]
    tabla.setStyle(TableStyle(orden))
    return tabla


def _fila_dato(etiqueta: str, valor: Any, estilos: dict[str, ParagraphStyle]) -> list[Any]:
    return [
        Paragraph(escape(etiqueta), estilos["etiqueta"]),
        Paragraph(escape(_texto(valor)), estilos["celda"]),
    ]


def _seccion(titulo: str, estilos: dict[str, ParagraphStyle]) -> list[Any]:
    """Título de sección con filete; evita que quede solo al pie de página."""
    return [
        CondPageBreak(34 * mm),
        Paragraph(titulo, estilos["seccion"]),
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.HexColor(BORDE),
            spaceAfter=5,
        ),
    ]


# ----------------------------------------------------------------------------
# Documento
# ----------------------------------------------------------------------------
def _crear_canvas(fuentes: _Fuentes, generado: dt.date):
    """Canvas con pie de página y numeración «Página X de Y»."""

    class CanvasNumerado(canvas.Canvas):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._paginas: list[dict[str, Any]] = []

        def showPage(self) -> None:  # noqa: N802 - API de ReportLab
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self) -> None:
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                self._dibujar_pie(total)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def _dibujar_pie(self, total: int) -> None:
            self.saveState()
            ancho, _alto = A4
            self.setStrokeColor(colors.HexColor(BORDE))
            self.setLineWidth(0.5)
            self.line(18 * mm, 15.5 * mm, ancho - 18 * mm, 15.5 * mm)

            self.setFont(fuentes.cuerpo, 7.2)
            self.setFillColor(colors.HexColor(GRIS_TENUE))
            self.drawString(
                18 * mm,
                11.3 * mm,
                "Bellum · Catálogo de Guerras de la Historia",
            )
            self.drawCentredString(
                ancho / 2,
                11.3 * mm,
                f"Ficha generada el {generado.strftime('%d/%m/%Y')}",
            )
            self.drawRightString(
                ancho - 18 * mm,
                11.3 * mm,
                f"Página {self._pageNumber} de {total}",
            )
            self.restoreState()

    return CanvasNumerado


def generar_pdf_guerra(
    datos: dict[str, Any], generado: dt.date | None = None
) -> bytes:
    """Devuelve el PDF completo de una guerra como bytes.

    ``datos`` es la estructura que devuelve ``RepositorioGuerras.obtener``:
    las claves ``guerra``, ``bandos``, ``participaciones``, ``batallas`` y
    ``tratados``.
    """
    if not REPORTLAB_DISPONIBLE:
        raise ErrorCatalogo(MENSAJE_SIN_REPORTLAB)

    guerra = datos.get("guerra") or {}
    bandos = datos.get("bandos") or []
    participaciones = datos.get("participaciones") or []
    batallas = datos.get("batallas") or []
    tratados = datos.get("tratados") or []
    generado = generado or dt.date.today()

    fuentes = _registrar_fuentes()
    estilos = _estilos(fuentes)

    total_tropas = sum(p.get("tropas") or 0 for p in participaciones)
    total_bajas = sum(p.get("bajas") or 0 for p in participaciones)
    if not total_bajas:
        total_bajas = guerra.get("bajas_totales") or 0

    historia: list[Any] = []

    # --- Banda de marca ---------------------------------------------------
    banda = Table(
        [
            [
                Paragraph(
                    escape(
                        "BELLUM  ·  CATÁLOGO DE GUERRAS DE LA HISTORIA"
                    ),
                    estilos["marca"],
                )
            ]
        ],
        colWidths=[174 * mm],
    )
    banda.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(AZUL)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    historia.append(banda)
    historia.append(Spacer(1, 9))

    # --- Título -----------------------------------------------------------
    historia.append(
        Paragraph(escape(_texto(guerra.get("nombre"), "Guerra")), estilos["titulo"])
    )
    resumen = " · ".join(
        parte
        for parte in (
            _texto(guerra.get("tipo"), ""),
            _texto(guerra.get("region"), ""),
            rango_anios(guerra.get("anio_inicio"), guerra.get("anio_fin")),
        )
        if parte
    )
    historia.append(Paragraph(escape(resumen), estilos["subtitulo"]))
    if guerra.get("siglo"):
        historia.append(
            Paragraph(
                escape(f"Siglo {guerra.get('siglo')}"),
                estilos["subtitulo"],
            )
        )
    historia.append(Spacer(1, 3))
    historia.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor(AZUL),
            spaceBefore=1,
            spaceAfter=7,
        )
    )

    # --- Ficha de datos ---------------------------------------------------
    historia.extend(_seccion("Ficha de datos", estilos))

    tropas_texto = numero(total_tropas) if total_tropas else "—"
    filas_datos = [
        _fila_dato("Tipo", guerra.get("tipo"), estilos),
        _fila_dato("Región", guerra.get("region"), estilos),
        _fila_dato("Continente", guerra.get("continente"), estilos),
        _fila_dato("Lugar", guerra.get("lugar"), estilos),
        _fila_dato(
            "Inicio",
            anio_texto(guerra.get("anio_inicio"))
            + (
                f" ({fecha_larga(guerra.get('fecha_inicio'))})"
                if guerra.get("fecha_inicio")
                else ""
            ),
            estilos,
        ),
        _fila_dato(
            "Fin",
            (
                anio_texto(guerra.get("anio_fin"))
                + (
                    f" ({fecha_larga(guerra.get('fecha_fin'))})"
                    if guerra.get("fecha_fin")
                    else ""
                )
                if guerra.get("anio_fin")
                else "En curso"
            ),
            estilos,
        ),
        _fila_dato(
            "Duración",
            duracion(guerra.get("anio_inicio"), guerra.get("anio_fin")),
            estilos,
        ),
        _fila_dato("Siglo", guerra.get("siglo"), estilos),
        _fila_dato("Tropas", tropas_texto, estilos),
        _fila_dato("Bajas", numero(total_bajas), estilos),
        _fila_dato("Resultado", guerra.get("resultado"), estilos),
        _fila_dato("Países participantes", guerra.get("num_paises"), estilos),
        _fila_dato("Batallas", guerra.get("num_batallas"), estilos),
        _fila_dato("Tratados", guerra.get("num_tratados"), estilos),
    ]

    # Se muestran en dos columnas de pares etiqueta/valor.
    mitad = (len(filas_datos) + 1) // 2
    filas_ficha: list[list[Any]] = []
    for indice in range(mitad):
        izquierda = filas_datos[indice]
        derecha = (
            filas_datos[indice + mitad]
            if indice + mitad < len(filas_datos)
            else [
                Paragraph("", estilos["etiqueta"]),
                Paragraph("", estilos["celda"]),
            ]
        )
        filas_ficha.append(izquierda + derecha)

    tabla_ficha = Table(
        filas_ficha,
        colWidths=[31 * mm, 54 * mm, 31 * mm, 58 * mm],
        hAlign="LEFT",
    )
    tabla_ficha.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(BORDE)),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(FONDO_SUAVE)),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(FONDO_SUAVE)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    historia.append(tabla_ficha)

    # --- Contexto ---------------------------------------------------------
    historia.append(Spacer(1, 4))
    historia.extend(_seccion("Contexto histórico", estilos))
    parrafos = _parrafos(guerra.get("descripcion"), estilos["cuerpo"])
    if parrafos:
        historia.extend(parrafos)
    else:
        historia.append(
            Paragraph(
                "Este artículo necesita ampliación: todavía no se ha registrado "
                "una descripción histórica del conflicto.",
                estilos["aviso"],
            )
        )

    # --- Bandos y participantes ------------------------------------------
    historia.extend(_seccion("Bandos y participantes", estilos))

    if bandos:
        for bando in bandos:
            nombre_bando = _texto(bando.get("nombre"), "Bando")
            resultado_bando = bando.get("resultado")
            titulo_bando = nombre_bando + (
                f"  —  {resultado_bando}" if resultado_bando else ""
            )
            bloque: list[Any] = [
                Paragraph(escape(titulo_bando), estilos["bando"])
            ]

            filas_bando = [
                p
                for p in participaciones
                if p.get("bando") == nombre_bando
            ]
            if filas_bando:
                bloque.append(
                    _tabla(
                        ["País o entidad", "Tropas", "Bajas"],
                        [
                            [
                                _texto(p.get("pais")),
                                numero(p.get("tropas")),
                                numero(p.get("bajas")),
                            ]
                            for p in filas_bando
                        ],
                        [104 * mm, 35 * mm, 35 * mm],
                        estilos,
                    )
                )
            else:
                bloque.append(
                    Paragraph(
                        "No hay países asociados a este bando en el catálogo.",
                        estilos["aviso"],
                    )
                )
            historia.append(KeepTogether(bloque))
    else:
        historia.append(
            Paragraph(
                "No se han registrado bandos para esta guerra.",
                estilos["aviso"],
            )
        )

    # --- Batallas ---------------------------------------------------------
    historia.extend(_seccion("Batallas", estilos))
    if batallas:
        filas_batallas: list[list[Any]] = []
        for batalla in batallas:
            detalle = _texto(batalla.get("descripcion"), "")
            celda_batalla = Paragraph(
                escape(_texto(batalla.get("nombre")))
                + (
                    f'<br/><font size="7.2" color="{GRIS_TENUE}">'
                    f"{escape(detalle)}</font>"
                    if detalle
                    else ""
                ),
                estilos["celda"],
            )
            filas_batallas.append(
                [
                    anio_texto(batalla.get("anio")),
                    celda_batalla,
                    _texto(batalla.get("lugar")),
                    _texto(batalla.get("resultado")),
                ]
            )
        historia.append(
            _tabla(
                ["Año", "Batalla", "Lugar", "Resultado"],
                filas_batallas,
                [16 * mm, 66 * mm, 44 * mm, 48 * mm],
                estilos,
            )
        )
    else:
        historia.append(
            Paragraph(
                "Sin batallas documentadas: el conflicto aparece en el catálogo "
                "sin enfrentamientos concretos registrados.",
                estilos["aviso"],
            )
        )

    # --- Tratados ---------------------------------------------------------
    historia.extend(_seccion("Tratados y consecuencias", estilos))
    if tratados:
        historia.append(
            _tabla(
                ["Año", "Tratado", "Lugar", "Descripción"],
                [
                    [
                        anio_texto(tratado.get("anio")),
                        _texto(tratado.get("nombre")),
                        _texto(tratado.get("lugar")),
                        _texto(tratado.get("descripcion")),
                    ]
                    for tratado in tratados
                ],
                [16 * mm, 50 * mm, 34 * mm, 74 * mm],
                estilos,
            )
        )
    else:
        historia.append(
            Paragraph(
                "No consta ningún tratado asociado a este conflicto en el catálogo.",
                estilos["aviso"],
            )
        )

    # --- Cronología -------------------------------------------------------
    cronologia: list[dict[str, Any]] = []
    for batalla in batallas:
        cronologia.append(
            {
                "anio": batalla.get("anio"),
                "tipo": "Batalla",
                "titulo": batalla.get("nombre"),
                "lugar": batalla.get("lugar"),
                "detalle": batalla.get("resultado"),
            }
        )
    for tratado in tratados:
        cronologia.append(
            {
                "anio": tratado.get("anio"),
                "tipo": "Tratado",
                "titulo": tratado.get("nombre"),
                "lugar": tratado.get("lugar"),
                "detalle": None,
            }
        )
    cronologia.sort(key=lambda f: (f["anio"] is None, f["anio"] or 0))

    historia.extend(_seccion("Cronología", estilos))
    if cronologia:
        historia.append(
            _tabla(
                ["Año", "Tipo", "Hito", "Lugar", "Detalle"],
                [
                    [
                        anio_texto(hito.get("anio")),
                        _texto(hito.get("tipo"), ""),
                        _texto(hito.get("titulo")),
                        _texto(hito.get("lugar")),
                        _texto(hito.get("detalle")),
                    ]
                    for hito in cronologia
                ],
                [16 * mm, 20 * mm, 60 * mm, 32 * mm, 46 * mm],
                estilos,
            )
        )
    else:
        historia.append(
            Paragraph(
                "No hay hitos cronológicos registrados para este conflicto.",
                estilos["aviso"],
            )
        )

    # --- Pie del documento ------------------------------------------------
    historia.append(Spacer(1, 6))
    historia.append(
        HRFlowable(
            width="100%", thickness=0.5, color=colors.HexColor(BORDE), spaceAfter=4
        )
    )
    historia.append(
        Paragraph(
            "Documento generado automáticamente desde la base de datos "
            "«catalogo_guerras» del proyecto Catálogo de Guerras de la Historia. "
            "Las cifras de bajas y tropas son estimaciones históricas y pueden "
            "variar según la fuente consultada.",
            estilos["pie"],
        )
    )

    # --- Construcción del PDF --------------------------------------------
    buffer = io.BytesIO()
    ancho, alto = A4
    documento = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=19 * mm,
        title=f"{_texto(guerra.get('nombre'), 'Guerra')} · Catálogo de Guerras",
        author="Catálogo de Guerras de la Historia",
        subject="Ficha histórica del conflicto",
        creator="Bellum · Flask + ReportLab",
    )
    marco = Frame(
        documento.leftMargin,
        documento.bottomMargin,
        documento.width,
        documento.height,
        id="cuerpo",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    documento.addPageTemplates([PageTemplate(id="ficha", frames=[marco])])
    documento.build(historia, canvasmaker=_crear_canvas(fuentes, generado))
    return buffer.getvalue()


def nombre_archivo_pdf(guerra: dict[str, Any]) -> str:
    """Nombre ASCII y seguro para la descarga: guerra-12-guerra-de-crimea.pdf."""
    identificador = guerra.get("id_guerra", "")
    base = f"guerra-{identificador}-{guerra.get('nombre', 'conflicto')}"
    base = unicodedata.normalize("NFKD", base)
    base = base.encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "-", base).strip("-").lower()
    return f"{base[:80].strip('-') or 'guerra'}.pdf"
