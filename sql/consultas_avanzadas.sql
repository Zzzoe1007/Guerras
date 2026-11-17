-- ============================================================================
-- CONSULTAS AVANZADAS / REPORTES
-- Catálogo de Guerras de la Historia
--
-- Este archivo se puede ejecutar directamente en phpMyAdmin (pestaña SQL)
-- después de importar catalogo_guerras.sql. Todas las consultas están
-- pensadas para MySQL 8.0+ (usan CTE y funciones de ventana).
-- ============================================================================

USE catalogo_guerras;

-- ----------------------------------------------------------------------------
-- 1. RESUMEN GENERAL DEL CATÁLOGO
-- ----------------------------------------------------------------------------
SELECT
    (SELECT COUNT(*) FROM guerras)                          AS total_guerras,
    (SELECT COUNT(*) FROM paises)                           AS total_paises,
    (SELECT COUNT(*) FROM participaciones)                  AS participaciones,
    (SELECT COUNT(*) FROM batallas)                         AS total_batallas,
    (SELECT COUNT(*) FROM tratados)                         AS total_tratados,
    (SELECT COUNT(*) FROM guerras WHERE anio_fin IS NULL)   AS guerras_en_curso,
    (SELECT COALESCE(SUM(bajas_totales), 0) FROM guerras)   AS bajas_registradas;

-- ----------------------------------------------------------------------------
-- 2. FILTRAR GUERRAS POR SIGLO
--    Cambiar 'XX' por 'XIX', 'XVIII', 'V a.C.', etc.
-- ----------------------------------------------------------------------------
SELECT
    id_guerra,
    nombre,
    anio_inicio,
    anio_fin,
    tipo,
    region,
    bajas_totales
FROM vw_guerras_detalle
WHERE siglo = 'XX'
ORDER BY anio_inicio;

-- ----------------------------------------------------------------------------
-- 3. FILTRAR GUERRAS POR REGIÓN
-- ----------------------------------------------------------------------------
SELECT
    id_guerra,
    nombre,
    anio_inicio,
    anio_fin,
    siglo,
    tipo,
    bajas_totales
FROM vw_guerras_detalle
WHERE region = 'Europa'
ORDER BY anio_inicio;

-- ----------------------------------------------------------------------------
-- 4. BUSCAR GUERRAS POR BANDO
--    Ejemplo: todos los conflictos en los que participó un bando "Aliados".
-- ----------------------------------------------------------------------------
SELECT DISTINCT
    g.id_guerra,
    g.nombre AS guerra,
    g.anio_inicio,
    g.anio_fin,
    b.nombre AS bando,
    b.resultado AS resultado_bando
FROM guerras g
INNER JOIN bandos b ON b.id_guerra = g.id_guerra
WHERE b.nombre LIKE '%Aliados%'
ORDER BY g.anio_inicio;

-- ----------------------------------------------------------------------------
-- 5. TOP 10 GUERRAS CON MÁS BAJAS REGISTRADAS
-- ----------------------------------------------------------------------------
SELECT
    nombre,
    siglo,
    region,
    bajas_totales
FROM vw_guerras_detalle
WHERE bajas_totales IS NOT NULL
ORDER BY bajas_totales DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 6. GUERRAS POR SIGLO CON TOTAL ACUMULADO (función de ventana)
-- ----------------------------------------------------------------------------
WITH por_siglo AS (
    SELECT
        siglo,
        MIN(anio_inicio) AS primer_anio,
        COUNT(*)         AS total_guerras,
        SUM(COALESCE(bajas_totales, 0)) AS bajas
    FROM guerras
    GROUP BY siglo
)
SELECT
    siglo,
    primer_anio,
    total_guerras,
    bajas,
    SUM(total_guerras) OVER (ORDER BY primer_anio) AS guerras_acumuladas
FROM por_siglo
ORDER BY primer_anio;

-- ----------------------------------------------------------------------------
-- 7. TOP 3 GUERRAS MÁS LETALES DE CADA REGIÓN (CTE + RANK)
-- ----------------------------------------------------------------------------
WITH ranking AS (
    SELECT
        r.nombre        AS region,
        g.nombre        AS guerra,
        g.bajas_totales,
        RANK() OVER (
            PARTITION BY g.id_region
            ORDER BY g.bajas_totales DESC
        ) AS posicion
    FROM guerras g
    INNER JOIN regiones r ON r.id_region = g.id_region
    WHERE g.bajas_totales IS NOT NULL
)
SELECT region, posicion, guerra, bajas_totales
FROM ranking
WHERE posicion <= 3
ORDER BY region, posicion, guerra;

-- ----------------------------------------------------------------------------
-- 8. PAÍSES CON MÁS PARTICIPACIONES EN GUERRAS
-- ----------------------------------------------------------------------------
SELECT
    p.nombre AS pais,
    COUNT(DISTINCT pa.id_guerra) AS guerras,
    COALESCE(SUM(pa.bajas), 0)   AS bajas_registradas
FROM paises p
INNER JOIN participaciones pa ON pa.id_pais = p.id_pais
GROUP BY p.id_pais, p.nombre
ORDER BY guerras DESC, bajas_registradas DESC, p.nombre
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 9. PAÍSES CON MÁS BANDOS VICTORIOSOS
-- ----------------------------------------------------------------------------
SELECT
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
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 10. GUERRAS SIN BATALLAS REGISTRADAS (LEFT JOIN + IS NULL)
-- ----------------------------------------------------------------------------
SELECT
    g.id_guerra,
    g.nombre,
    g.anio_inicio,
    g.anio_fin
FROM guerras g
LEFT JOIN batallas b ON b.id_guerra = g.id_guerra
WHERE b.id_batalla IS NULL
ORDER BY g.anio_inicio;

-- ----------------------------------------------------------------------------
-- 11. GUERRAS DE UN PAÍS CONCRETO (ejemplo: Perú, id_pais = 37)
-- ----------------------------------------------------------------------------
SELECT
    g.nombre AS guerra,
    g.anio_inicio,
    g.anio_fin,
    b.nombre AS bando,
    b.resultado AS resultado_bando
FROM participaciones pa
INNER JOIN guerras g ON g.id_guerra = pa.id_guerra
INNER JOIN bandos b
        ON b.id_bando = pa.id_bando
       AND b.id_guerra = pa.id_guerra
WHERE pa.id_pais = 37
ORDER BY g.anio_inicio;

-- ----------------------------------------------------------------------------
-- 12. DISTRIBUCIÓN PORCENTUAL DE GUERRAS POR TIPO
-- ----------------------------------------------------------------------------
SELECT
    t.nombre AS tipo,
    COUNT(g.id_guerra) AS total,
    ROUND(
        100.0 * COUNT(g.id_guerra) / (SELECT COUNT(*) FROM guerras),
        1
    ) AS porcentaje
FROM tipos_guerra t
LEFT JOIN guerras g ON g.id_tipo = t.id_tipo
GROUP BY t.id_tipo, t.nombre
ORDER BY total DESC, t.nombre;

-- ----------------------------------------------------------------------------
-- 13. GUERRAS MÁS LARGAS (DURACIÓN APROXIMADA EN AÑOS)
-- ----------------------------------------------------------------------------
SELECT
    nombre,
    anio_inicio,
    anio_fin,
    (COALESCE(anio_fin, YEAR(CURDATE())) - anio_inicio) AS duracion_anios
FROM guerras
ORDER BY duracion_anios DESC, anio_inicio
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 14. CONFLICTOS AÚN ABIERTOS
-- ----------------------------------------------------------------------------
SELECT
    id_guerra,
    nombre,
    anio_inicio,
    siglo,
    region,
    resultado
FROM vw_guerras_detalle
WHERE anio_fin IS NULL
ORDER BY anio_inicio;

-- ----------------------------------------------------------------------------
-- 15. DETALLE COMPLETO DE UNA GUERRA (ejemplo: Segunda Guerra Mundial)
-- ----------------------------------------------------------------------------
SELECT *
FROM vw_guerras_detalle
WHERE nombre = 'Segunda Guerra Mundial';

SELECT
    b.nombre AS bando,
    b.resultado AS resultado_bando,
    p.nombre AS pais,
    pa.tropas,
    pa.bajas
FROM participaciones pa
INNER JOIN bandos b
        ON b.id_bando = pa.id_bando
       AND b.id_guerra = pa.id_guerra
INNER JOIN paises p ON p.id_pais = pa.id_pais
WHERE pa.id_guerra = 22
ORDER BY b.nombre, p.nombre;
