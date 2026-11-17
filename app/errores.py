"""Excepciones propias del catálogo."""

from __future__ import annotations


class ErrorCatalogo(Exception):
    """Error de negocio controlado que se puede mostrar al usuario."""


class ErrorValidacion(ErrorCatalogo):
    """Los datos enviados por el usuario no son válidos."""


class ErrorNoEncontrado(ErrorCatalogo):
    """El registro solicitado no existe."""


class ErrorConflicto(ErrorCatalogo):
    """La operación choca con una restricción (duplicados, claves foráneas)."""
