-- ============================================================================
-- PROYECTO: Catálogo de Guerras de la Historia
-- MOTOR: MySQL 8.0+ / MariaDB 10.5+ (compatible con phpMyAdmin)
-- AUTOR: Proyecto académico
-- DESCRIPCIÓN: Esquema relacional normalizado, datos históricos de prueba,
--              vistas de consulta y reportes de ejemplo.
--
-- IMPORTANTE:
--   * Los años anteriores a Cristo se guardan como números negativos
--     (ej.: -499 = 499 a.C.).
--   * MySQL no permite fechas DATE anteriores al año 1000, por eso las
--     guerras antiguas usan fecha_inicio/fecha_fin = NULL y se ordenan
--     por anio_inicio.
--   * Las cifras de bajas son estimaciones históricas aproximadas.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS catalogo_guerras
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE catalogo_guerras;

ALTER DATABASE catalogo_guerras
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

SET NAMES utf8mb4;

-- ----------------------------------------------------------------------------
-- Limpieza para permitir reimportar el script sin errores
-- ----------------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS vw_resumen_region;
DROP VIEW IF EXISTS vw_resumen_siglo;
DROP VIEW IF EXISTS vw_bandos_participantes;
DROP VIEW IF EXISTS vw_guerras_detalle;

DROP TABLE IF EXISTS participaciones;
DROP TABLE IF EXISTS tratados;
DROP TABLE IF EXISTS batallas;
DROP TABLE IF EXISTS bandos;
DROP TABLE IF EXISTS guerras;
DROP TABLE IF EXISTS paises;
DROP TABLE IF EXISTS tipos_guerra;
DROP TABLE IF EXISTS regiones;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 1. TABLAS CATÁLOGO
-- ----------------------------------------------------------------------------

CREATE TABLE regiones (
    id_region     INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(60)  NOT NULL UNIQUE,
    continente    VARCHAR(40)  NOT NULL,
    descripcion   VARCHAR(200) NULL
) ENGINE = InnoDB;

CREATE TABLE tipos_guerra (
    id_tipo       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(80)  NOT NULL UNIQUE,
    descripcion   VARCHAR(250) NULL
) ENGINE = InnoDB;

CREATE TABLE paises (
    id_pais       INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(120) NOT NULL UNIQUE,
    codigo_iso2   CHAR(2)      NULL,
    continente    VARCHAR(40)  NOT NULL,
    vigente       BOOLEAN      NOT NULL DEFAULT TRUE,
    notas         VARCHAR(200) NULL,
    CONSTRAINT chk_paises_vigente CHECK (vigente IN (0, 1))
) ENGINE = InnoDB;

-- ----------------------------------------------------------------------------
-- 2. TABLA PRINCIPAL: GUERRAS
-- ----------------------------------------------------------------------------

CREATE TABLE guerras (
    id_guerra      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(150) NOT NULL UNIQUE,
    anio_inicio    SMALLINT     NOT NULL,
    anio_fin       SMALLINT     NULL,
    fecha_inicio   DATE         NULL,
    fecha_fin      DATE         NULL,
    siglo          VARCHAR(20)  NOT NULL,
    id_tipo        INT UNSIGNED NOT NULL,
    id_region      INT UNSIGNED NOT NULL,
    lugar          VARCHAR(180) NOT NULL,
    resultado      VARCHAR(220) NULL,
    bajas_totales  INT UNSIGNED NULL,
    descripcion    TEXT         NULL,
    creado_en      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_guerras_tipo
        FOREIGN KEY (id_tipo) REFERENCES tipos_guerra (id_tipo)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_guerras_region
        FOREIGN KEY (id_region) REFERENCES regiones (id_region)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT chk_guerras_anios
        CHECK (anio_inicio <> 0 AND (anio_fin IS NULL OR anio_fin >= anio_inicio)),
    CONSTRAINT chk_guerras_fechas
        CHECK (fecha_fin IS NULL OR fecha_inicio IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT chk_guerras_bajas
        CHECK (bajas_totales IS NULL OR bajas_totales >= 0),

    INDEX idx_guerras_anio (anio_inicio),
    INDEX idx_guerras_siglo (siglo),
    INDEX idx_guerras_tipo (id_tipo),
    INDEX idx_guerras_region (id_region)
) ENGINE = InnoDB;

-- ----------------------------------------------------------------------------
-- 3. BANDOS DE CADA GUERRA
--    Cada guerra puede tener dos o más bandos. El resultado se guarda por
--    bando para poder explotar estadísticas de victorias por país.
-- ----------------------------------------------------------------------------

CREATE TABLE bandos (
    id_bando      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_guerra     INT UNSIGNED NOT NULL,
    nombre        VARCHAR(120) NOT NULL,
    resultado     ENUM('Victoria', 'Derrota', 'Indeciso', 'En curso') NULL,
    descripcion   VARCHAR(250) NULL,

    CONSTRAINT fk_bandos_guerra
        FOREIGN KEY (id_guerra) REFERENCES guerras (id_guerra)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_bandos_guerra_nombre UNIQUE (id_guerra, nombre),
    -- Necesario para la clave foránea compuesta de participaciones:
    CONSTRAINT uq_bandos_id_guerra UNIQUE (id_bando, id_guerra)
) ENGINE = InnoDB;

-- ----------------------------------------------------------------------------
-- 4. PARTICIPACIÓN DE PAÍSES EN LAS GUERRAS (N:M)
--    La FK compuesta (id_bando, id_guerra) impide asociar un país a un bando
--    que pertenece a otra guerra.
-- ----------------------------------------------------------------------------

CREATE TABLE participaciones (
    id_participacion INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_guerra        INT UNSIGNED NOT NULL,
    id_pais          INT UNSIGNED NOT NULL,
    id_bando         INT UNSIGNED NOT NULL,
    tropas           INT UNSIGNED NULL,
    bajas            INT UNSIGNED NULL,
    CONSTRAINT fk_part_guerra
        FOREIGN KEY (id_guerra) REFERENCES guerras (id_guerra)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_part_pais
        FOREIGN KEY (id_pais) REFERENCES paises (id_pais)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_part_bando_guerra
        FOREIGN KEY (id_bando, id_guerra) REFERENCES bandos (id_bando, id_guerra)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT uq_part_guerra_pais UNIQUE (id_guerra, id_pais),
    CONSTRAINT chk_part_bajas CHECK (bajas IS NULL OR bajas >= 0),
    INDEX idx_part_pais (id_pais)
) ENGINE = InnoDB;

-- ----------------------------------------------------------------------------
-- 5. BATALLAS Y TRATADOS
-- ----------------------------------------------------------------------------

CREATE TABLE batallas (
    id_batalla    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_guerra     INT UNSIGNED NOT NULL,
    nombre        VARCHAR(150) NOT NULL,
    anio          SMALLINT     NOT NULL,
    fecha         DATE         NULL,
    lugar         VARCHAR(150) NULL,
    resultado     VARCHAR(180) NULL,
    descripcion   TEXT         NULL,

    CONSTRAINT fk_batallas_guerra
        FOREIGN KEY (id_guerra) REFERENCES guerras (id_guerra)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_batallas_anio CHECK (anio <> 0),
    INDEX idx_batallas_guerra (id_guerra),
    INDEX idx_batallas_anio (anio)
) ENGINE = InnoDB;

CREATE TABLE tratados (
    id_tratado    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_guerra     INT UNSIGNED NOT NULL,
    nombre        VARCHAR(160) NOT NULL,
    anio          SMALLINT     NULL,
    lugar         VARCHAR(120) NULL,
    descripcion   TEXT         NULL,

    CONSTRAINT fk_tratados_guerra
        FOREIGN KEY (id_guerra) REFERENCES guerras (id_guerra)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT chk_tratados_anio CHECK (anio IS NULL OR anio <> 0),
    INDEX idx_tratados_guerra (id_guerra)
) ENGINE = InnoDB;

-- ============================================================================
-- DATOS DE PRUEBA
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Regiones
-- ----------------------------------------------------------------------------
INSERT INTO regiones (id_region, nombre, continente, descripcion) VALUES
(1, 'Europa',   'Europa',   'Conflictos ocurridos total o principalmente en Europa.'),
(2, 'Asia',     'Asia',     'Conflictos ocurridos total o principalmente en Asia.'),
(3, 'África',   'África',   'Conflictos ocurridos total o principalmente en África.'),
(4, 'América',  'América',  'Conflictos ocurridos total o principalmente en América.'),
(5, 'Oceanía',  'Oceanía',  'Conflictos ocurridos total o principalmente en Oceanía.'),
(6, 'Mundial',  'Varios',   'Conflictos con teatros de operaciones en varios continentes.');

-- ----------------------------------------------------------------------------
-- Tipos de guerra
-- ----------------------------------------------------------------------------
INSERT INTO tipos_guerra (id_tipo, nombre, descripcion) VALUES
(1, 'Guerra de independencia', 'Conflicto por la separación política de un territorio respecto de otro Estado.'),
(2, 'Guerra civil',            'Enfrentamiento armado entre grupos organizados dentro de un mismo Estado.'),
(3, 'Guerra religiosa',        'Conflicto cuyo motivo principal es la imposición o defensa de una confesión religiosa.'),
(4, 'Guerra de conquista',     'Campaña militar destinada a anexar territorio o someter a otro pueblo.'),
(5, 'Guerra mundial',          'Guerra de gran escala con participación de potencias de varios continentes.'),
(6, 'Guerra colonial',         'Conflicto entre una potencia colonial y un territorio sometido o entre imperios.'),
(7, 'Guerra de sucesión',      'Guerra provocada por la disputa de un trono o de una herencia dinástica.'),
(8, 'Guerra interestatal',    'Enfrentamiento armado entre dos o más Estados soberanos.');

-- ----------------------------------------------------------------------------
-- Países y entidades históricas
-- ----------------------------------------------------------------------------
INSERT INTO paises (id_pais, nombre, codigo_iso2, continente, vigente, notas) VALUES
(1,  'Antigua Grecia',                     NULL, 'Europa',  0, 'Conjunto de polis griegas.'),
(2,  'Imperio Persa',                      NULL, 'Asia',    0, 'Imperio aqueménida y posteriores.'),
(3,  'Atenas',                             NULL, 'Europa',  0, 'Poleis griega, hoy capital de Grecia.'),
(4,  'Esparta',                            NULL, 'Europa',  0, 'Poleis griega del Peloponeso.'),
(5,  'Reino de Macedonia',                 NULL, 'Europa',  0, 'Reino de Filipo II y Alejandro Magno.'),
(6,  'República Romana',                   NULL, 'Europa',  0, 'Roma antes del Imperio.'),
(7,  'Cartago',                            NULL, 'África',  0, 'Ciudad-estado fenicia del norte de África.'),
(8,  'Galia',                              NULL, 'Europa',  0, 'Territorio de los pueblos galos.'),
(9,  'Reino de Inglaterra',                NULL, 'Europa',  0, 'Entidad histórica anterior a 1707.'),
(10, 'Reino de Francia',                   NULL, 'Europa',  0, 'Monarquía francesa anterior a 1792.'),
(11, 'Imperio español',                    NULL, 'Europa',  0, 'Monarquía hispánica y sus dominios.'),
(12, 'Provincias Unidas',                  NULL, 'Europa',  0, 'República neerlandesa del siglo XVII.'),
(13, 'Sacro Imperio Romano Germánico',     NULL, 'Europa',  0, 'Entidad política de Europa central.'),
(14, 'Prusia',                             NULL, 'Europa',  0, 'Reino alemán anterior a la unificación.'),
(15, 'Imperio ruso',                       NULL, 'Europa',  0, 'Rusia zarista hasta 1917.'),
(16, 'Austria-Hungría',                    NULL, 'Europa',  0, 'Imperio dual disuelto en 1918.'),
(17, 'Imperio otomano',                    NULL, 'Asia',    0, 'Imperio turco disuelto en 1922.'),
(18, 'Unión Soviética',                    NULL, 'Europa',  0, 'Estado socialista disuelto en 1991.'),
(19, 'Vietnam del Norte',                  NULL, 'Asia',    0, 'República Democrática de Vietnam.'),
(20, 'Vietnam del Sur',                    NULL, 'Asia',    0, 'República de Vietnam (1955-1975).'),
(21, 'Estados Confederados de América',    NULL, 'América', 0, 'Estados secesionistas de 1861-1865.'),
(22, 'Repúblicas Bóeres',                  NULL, 'África',  0, 'Repúblicas del Transvaal y Orange.'),
(23, 'Reino Unido',                        'GB', 'Europa',  1, 'Reino Unido de Gran Bretaña e Irlanda del Norte.'),
(24, 'Francia',                            'FR', 'Europa',  1, 'República Francesa.'),
(25, 'Alemania',                           'DE', 'Europa',  1, 'República Federal de Alemania.'),
(26, 'Italia',                             'IT', 'Europa',  1, 'República Italiana.'),
(27, 'Rusia',                              'RU', 'Europa',  1, 'Federación de Rusia.'),
(28, 'Estados Unidos',                     'US', 'América', 1, 'Estados Unidos de América.'),
(29, 'Japón',                              'JP', 'Asia',    1, 'Estado de Japón.'),
(30, 'China',                              'CN', 'Asia',    1, 'República Popular China.'),
(31, 'Corea del Norte',                    'KP', 'Asia',    1, 'República Popular Democrática de Corea.'),
(32, 'Corea del Sur',                      'KR', 'Asia',    1, 'República de Corea.'),
(33, 'Vietnam',                            'VN', 'Asia',    1, 'República Socialista de Vietnam.'),
(34, 'Argentina',                          'AR', 'América', 1, 'República Argentina.'),
(35, 'España',                             'ES', 'Europa',  1, 'Reino de España.'),
(36, 'Chile',                              'CL', 'América', 1, 'República de Chile.'),
(37, 'Perú',                               'PE', 'América', 1, 'República del Perú.'),
(38, 'Bolivia',                            'BO', 'América', 1, 'Estado Plurinacional de Bolivia.'),
(39, 'Irak',                               'IQ', 'Asia',    1, 'República de Irak.'),
(40, 'Kuwait',                             'KW', 'Asia',    1, 'Estado de Kuwait.'),
(41, 'Serbia',                             'RS', 'Europa',  1, 'República de Serbia.'),
(42, 'Croacia',                            'HR', 'Europa',  1, 'República de Croacia.'),
(43, 'Bosnia y Herzegovina',               'BA', 'Europa',  1, 'Estado de Bosnia y Herzegovina.'),
(44, 'Afganistán',                         'AF', 'Asia',    1, 'Emirato Islámico de Afganistán.'),
(45, 'Ucrania',                            'UA', 'Europa',  1, 'Ucrania.'),
(46, 'Israel',                             'IL', 'Asia',    1, 'Estado de Israel.'),
(47, 'Egipto',                             'EG', 'África',  1, 'República Árabe de Egipto.'),
(48, 'Siria',                              'SY', 'Asia',    1, 'República Árabe Siria.'),
(49, 'Portugal',                           'PT', 'Europa',  1, 'República Portuguesa.'),
(50, 'Países Bajos',                       'NL', 'Europa',  1, 'Reino de los Países Bajos.'),
(51, 'Bélgica',                            'BE', 'Europa',  1, 'Reino de Bélgica.'),
(52, 'Austria',                            'AT', 'Europa',  1, 'República de Austria.'),
(53, 'Hungría',                            'HU', 'Europa',  1, 'Hungría.'),
(54, 'Canadá',                             'CA', 'América', 1, 'Canadá.'),
(55, 'Australia',                          'AU', 'Oceanía', 1, 'Mancomunidad de Australia.'),
(56, 'India',                              'IN', 'Asia',    1, 'República de la India.'),
(57, 'Pakistán',                           'PK', 'Asia',    1, 'República Islámica de Pakistán.'),
(58, 'México',                             'MX', 'América', 1, 'Estados Unidos Mexicanos.'),
(59, 'Colombia',                           'CO', 'América', 1, 'República de Colombia.'),
(60, 'Venezuela',                          'VE', 'América', 1, 'República Bolivariana de Venezuela.'),
(61, 'Ecuador',                            'EC', 'América', 1, 'República del Ecuador.'),
(62, 'Suecia',                             'SE', 'Europa',  1, 'Reino de Suecia.'),
(63, 'Dinamarca',                          'DK', 'Europa',  1, 'Reino de Dinamarca.'),
(64, 'Jordania',                           'JO', 'Asia',    1, 'Reino Hachemita de Jordania.'),
(65, 'Arabia Saudita',                     'SA', 'Asia',    1, 'Reino de Arabia Saudita.'),
(66, 'Eslovenia',                          'SI', 'Europa',  1, 'República de Eslovenia.'),
(67, 'Argelia',                            'DZ', 'África',  1, 'República Argelina Democrática y Popular.'),
(68, 'Irán',                               'IR', 'Asia',    1, 'República Islámica de Irán.'),
(69, 'Paraguay',                           'PY', 'América', 1, 'República del Paraguay.'),
(70, 'Oposición siria',                    NULL, 'Asia',    0, 'Coalición de grupos opositores al régimen sirio.');

-- ----------------------------------------------------------------------------
-- Guerras (34 conflictos representativos de distintas épocas)
-- Columnas: id, nombre, anio_inicio, anio_fin, fecha_inicio, fecha_fin,
--           siglo, id_tipo, id_region, lugar, resultado, bajas, descripcion
-- ----------------------------------------------------------------------------
INSERT INTO guerras
(id_guerra, nombre, anio_inicio, anio_fin, fecha_inicio, fecha_fin, siglo,
 id_tipo, id_region, lugar, resultado, bajas_totales, descripcion) VALUES
(1, 'Guerras Médicas', -499, -449, NULL, NULL, 'V a.C.', 4, 1,
 'Grecia, Asia Menor y el mar Egeo', 'Victoria de la coalición griega', 200000,
 'Serie de conflictos entre las polis griegas y el Imperio Persa aqueménida, desde la revuelta jonia hasta la paz de Calias.'),
(2, 'Guerra del Peloponeso', -431, -404, NULL, NULL, 'V a.C.', 8, 1,
 'Antigua Grecia', 'Victoria de Esparta', 50000,
 'Enfrentamiento entre la Liga de Delos, liderada por Atenas, y la Liga del Peloponeso, encabezada por Esparta.'),
(3, 'Guerras de Alejandro Magno', -334, -323, NULL, NULL, 'IV a.C.', 4, 2,
 'Anatolia, Levante, Egipto, Mesopotamia y Persia', 'Victoria de Macedonia', 100000,
 'Campaña de Alejandro III de Macedonia contra el Imperio Persa, que dio origen al mundo helenístico.'),
(4, 'Guerras Púnicas', -264, -146, NULL, NULL, 'III a.C.', 4, 1,
 'Mediterráneo occidental', 'Victoria de Roma', 500000,
 'Tres guerras entre Roma y Cartago por el control del Mediterráneo occidental; terminaron con la destrucción de Cartago.'),
(5, 'Guerra de las Galias', -58, -50, NULL, NULL, 'I a.C.', 4, 1,
 'Galia (actual Francia, Bélgica y Suiza)', 'Victoria de Roma', 1000000,
 'Campaña de Julio César para someter a los pueblos galos y anexar su territorio a la República Romana.'),
(6, 'Guerra de los Cien Años', 1337, 1453, '1337-05-24', '1453-10-19', 'XIV', 7, 1,
 'Francia, Inglaterra y Países Bajos', 'Victoria de Francia', 3000000,
 'Conflicto dinástico entre las casas de Valois y Plantagenet por el trono de Francia, con episodios como Agincourt y Juana de Arco.'),
(7, 'Guerras Italianas', 1494, 1559, NULL, NULL, 'XV', 8, 1,
 'Península itálica', 'Victoria de España y el Sacro Imperio', 300000,
 'Serie de guerras entre Francia, España, el Sacro Imperio y los Estados italianos por la hegemonía en Italia.'),
(8, 'Guerra de los Treinta Años', 1618, 1648, '1618-05-23', '1648-10-24', 'XVII', 3, 1,
 'Europa central', 'Paz de Westfalia; equilibrio religioso', 8000000,
 'Guerra religiosa y política que devastó el Sacro Imperio y terminó con los tratados de Westfalia.'),
(9, 'Guerra de Sucesión Española', 1701, 1714, NULL, NULL, 'XVIII', 7, 1,
 'Europa occidental', 'Tratados de Utrecht y Rastatt', 400000,
 'Conflicto por la sucesión de Carlos II de España entre los Borbones y la Gran Alianza de Habsburgo, Inglaterra y Provincias Unidas.'),
(10, 'Guerra de los Siete Años', 1756, 1763, NULL, NULL, 'XVIII', 8, 6,
 'Europa, América del Norte, India y Caribe', 'Victoria británica; Paz de París', 1000000,
 'Primera guerra de escala global; enfrentó a Gran Bretaña y Prusia contra Francia, Austria y Rusia.'),
(11, 'Guerra de Independencia de los Estados Unidos', 1775, 1783, '1775-04-19', '1783-09-03', 'XVIII', 1, 4,
 'Trece Colonias de América del Norte', 'Independencia de los Estados Unidos', 100000,
 'Revuelta de las Trece Colonias contra el Reino de Gran Bretaña, con apoyo de Francia y España.'),
(12, 'Guerras Napoleónicas', 1803, 1815, '1803-05-18', '1815-11-20', 'XIX', 8, 1,
 'Europa y teatros coloniales', 'Derrota de Napoleón; Congreso de Viena', 3500000,
 'Serie de coaliciones europeas contra el Imperio francés de Napoleón Bonaparte, culminadas en Waterloo.'),
(13, 'Guerras de Independencia Hispanoamericanas', 1810, 1833, NULL, NULL, 'XIX', 1, 4,
 'América Latina', 'Independencia de las repúblicas hispanoamericanas', 600000,
 'Procesos independentistas contra el Imperio español en México, Sudamérica y Centroamérica.'),
(14, 'Primera Guerra del Opio', 1839, 1842, '1839-06-03', '1842-08-29', 'XIX', 6, 2,
 'China meridional', 'Victoria británica; Tratado de Nankín', 20000,
 'Guerra entre el Reino Unido y la dinastía Qing por el comercio de opio; abrió China a la influencia europea.'),
(15, 'Guerra de Crimea', 1853, 1856, '1853-10-16', '1856-03-30', 'XIX', 8, 1,
 'Península de Crimea y mar Negro', 'Victoria aliada; Tratado de París', 500000,
 'Enfrentamiento entre el Imperio ruso y una alianza de Francia, Reino Unido y el Imperio otomano.'),
(16, 'Guerra de Secesión', 1861, 1865, '1861-04-12', '1865-05-09', 'XIX', 2, 4,
 'Estados Unidos', 'Victoria de la Unión', 620000,
 'Guerra civil entre la Unión y los Estados Confederados, motivada por la esclavitud y la secesión del sur.'),
(17, 'Guerra del Pacífico', 1879, 1884, '1879-04-05', '1884-10-20', 'XIX', 8, 4,
 'Costa del Pacífico sudamericano', 'Victoria de Chile', 20000,
 'Guerra entre Chile y la alianza de Perú y Bolivia por el control del desierto de Atacama y sus recursos.'),
(18, 'Guerra de los Bóeres', 1899, 1902, '1899-10-11', '1902-05-31', 'XIX', 6, 3,
 'Sudáfrica', 'Victoria británica', 75000,
 'Conflicto entre el Imperio británico y las repúblicas bóeres del Transvaal y Orange.'),
(19, 'Guerra Ruso-Japonesa', 1904, 1905, '1904-02-08', '1905-09-05', 'XX', 8, 2,
 'Manchuria, Corea y mar Amarillo', 'Victoria japonesa; Tratado de Portsmouth', 150000,
 'Guerra entre el Imperio ruso y el Imperio del Japón por el control de Manchuria y Corea.'),
(20, 'Primera Guerra Mundial', 1914, 1918, '1914-07-28', '1918-11-11', 'XX', 5, 6,
 'Europa, Oriente Medio, África y océanos', 'Victoria de los Aliados', 17000000,
 'Gran guerra entre los Aliados y las Potencias Centrales; reconfiguró el mapa de Europa y Oriente Medio.'),
(21, 'Guerra del Chaco', 1932, 1935, '1932-09-09', '1935-06-12', 'XX', 8, 4,
 'Chaco Boreal', 'Victoria de Paraguay', 100000,
 'Guerra entre Bolivia y Paraguay por el control del Chaco Boreal, vinculada a la posible existencia de petróleo.'),
(22, 'Segunda Guerra Mundial', 1939, 1945, '1939-09-01', '1945-09-02', 'XX', 5, 6,
 'Europa, Asia, África, Oceanía y océanos', 'Victoria de los Aliados', 70000000,
 'Conflicto global entre los Aliados y el Eje; incluyó el Holocausto y los bombardeos atómicos de Hiroshima y Nagasaki.'),
(23, 'Guerra de Corea', 1950, 1953, '1950-06-25', '1953-07-27', 'XX', 8, 2,
 'Península de Corea', 'Armisticio; sin tratado de paz', 3000000,
 'Guerra entre Corea del Sur, apoyada por la ONU y Estados Unidos, y Corea del Norte, apoyada por China y la URSS.'),
(24, 'Guerra de Argelia', 1954, 1962, '1954-11-01', '1962-07-05', 'XX', 1, 3,
 'Argelia', 'Independencia de Argelia', 400000,
 'Guerra de liberación nacional del Frente de Liberación Nacional argelino contra Francia.'),
(25, 'Guerra de Vietnam', 1955, 1975, '1955-11-01', '1975-04-30', 'XX', 2, 2,
 'Vietnam, Laos y Camboya', 'Victoria de Vietnam del Norte', 3000000,
 'Guerra civil e internacional entre Vietnam del Norte y el Viet Cong contra Vietnam del Sur y sus aliados, especialmente Estados Unidos.'),
(26, 'Guerra de los Seis Días', 1967, 1967, '1967-06-05', '1967-06-10', 'XX', 8, 2,
 'Oriente Medio', 'Victoria de Israel', 25000,
 'Guerra entre Israel y Egipto, Siria y Jordania; Israel ocupó Sinaí, Cisjordania, Gaza y los Altos del Golán.'),
(27, 'Guerra de Yom Kipur', 1973, 1973, '1973-10-06', '1973-10-25', 'XX', 8, 2,
 'Sinaí y Altos del Golán', 'Alto el fuego; victoria militar israelí', 20000,
 'Ofensiva sorpresa de Egipto y Siria contra Israel durante la festividad judía de Yom Kipur.'),
(28, 'Guerra de las Malvinas', 1982, 1982, '1982-04-02', '1982-06-14', 'XX', 8, 4,
 'Islas Malvinas/Falkland', 'Victoria británica', 1000,
 'Guerra entre Argentina y el Reino Unido por la soberanía de las islas Malvinas/Falkland.'),
(29, 'Guerra del Golfo', 1990, 1991, '1990-08-02', '1991-02-28', 'XX', 8, 2,
 'Kuwait e Irak', 'Victoria de la coalición internacional', 100000,
 'Respuesta internacional a la invasión de Kuwait por Irak; incluyó la operación Tormenta del Desierto.'),
(30, 'Guerras Yugoslavas', 1991, 2001, '1991-06-25', '2001-11-12', 'XX', 2, 1,
 'Balcanes occidentales', 'Disolución de Yugoslavia', 130000,
 'Serie de guerras étnicas y políticas tras la desintegración de Yugoslavia, con episodios como el sitio de Sarajevo.'),
(31, 'Guerra de Afganistán', 2001, 2021, '2001-10-07', '2021-08-30', 'XXI', 8, 2,
 'Afganistán', 'Regreso del Talibán al poder', 176000,
 'Intervención liderada por Estados Unidos tras los atentados del 11 de septiembre, prolongada durante dos décadas.'),
(32, 'Guerra de Irak', 2003, 2011, '2003-03-20', '2011-12-15', 'XXI', 8, 2,
 'Irak', 'Caída del régimen de Sadam Huseín', 150000,
 'Invasión de Irak por una coalición liderada por Estados Unidos, que derrocó a Sadam Huseín.'),
(33, 'Guerra civil siria', 2011, NULL, '2011-03-15', NULL, 'XXI', 2, 2,
 'Siria', 'Conflicto en curso; caída del régimen de Al Asad en 2024', 500000,
 'Guerra civil e internacionalizada que comenzó con protestas contra el régimen de Bashar al-Asad.'),
(34, 'Invasión rusa de Ucrania', 2022, NULL, '2022-02-24', NULL, 'XXI', 8, 1,
 'Ucrania', 'En curso', NULL,
 'Invasión a gran escala de Ucrania por la Federación de Rusia, continuación de la guerra iniciada en 2014.');

-- ----------------------------------------------------------------------------
-- Bandos
-- ----------------------------------------------------------------------------
INSERT INTO bandos (id_bando, id_guerra, nombre, resultado, descripcion) VALUES
(11, 1, 'Liga Helénica', 'Victoria', 'Coalición de polis griegas, liderada por Atenas y Esparta.'),
(12, 1, 'Imperio Persa', 'Derrota', 'Imperio aqueménida de Darío I y Jerjes I.'),
(21, 2, 'Liga del Peloponeso', 'Victoria', 'Alianza liderada por Esparta.'),
(22, 2, 'Liga de Delos', 'Derrota', 'Alianza liderada por Atenas.'),
(31, 3, 'Reino de Macedonia', 'Victoria', 'Ejército de Alejandro Magno.'),
(32, 3, 'Imperio Persa', 'Derrota', 'Imperio de Darío III.'),
(41, 4, 'República Romana', 'Victoria', 'Roma y sus aliados itálicos.'),
(42, 4, 'Cartago', 'Derrota', 'Ciudad-estado y su imperio mediterráneo.'),
(51, 5, 'República Romana', 'Victoria', 'Legiones de Julio César.'),
(52, 5, 'Pueblos galos', 'Derrota', 'Confederación de tribus galas.'),
(61, 6, 'Reino de Inglaterra', 'Derrota', 'Casa de Plantagenet.'),
(62, 6, 'Reino de Francia', 'Victoria', 'Casa de Valois.'),
(71, 7, 'Francia y aliados', 'Derrota', 'Reino de Francia y Estados italianos aliados.'),
(72, 7, 'España y el Sacro Imperio', 'Victoria', 'Monarquía hispánica y Habsburgo austríacos.'),
(81, 8, 'Bando católico', 'Indeciso', 'Habsburgo, Liga Católica y aliados.'),
(82, 8, 'Bando protestante', 'Indeciso', 'Príncipes protestantes, Provincias Unidas, Suecia y Dinamarca.'),
(91, 9, 'Casa de Borbón', 'Indeciso', 'Francia y Felipe V de España.'),
(92, 9, 'Gran Alianza', 'Indeciso', 'Inglaterra, Provincias Unidas y Austria.'),
(101, 10, 'Gran Bretaña y Prusia', 'Victoria', 'Alianza anglo-prusiana.'),
(102, 10, 'Francia, Austria y Rusia', 'Derrota', 'Coalición franco-austro-rusa.'),
(111, 11, 'Trece Colonias y aliados', 'Victoria', 'Estados Unidos, Francia y España.'),
(112, 11, 'Reino de Gran Bretaña', 'Derrota', 'Ejército británico y auxiliares.'),
(121, 12, 'Coalición antifrancesa', 'Victoria', 'Reino Unido, Prusia, Rusia, Austria y España.'),
(122, 12, 'Imperio francés y aliados', 'Derrota', 'Francia napoleónica y Estados satélites.'),
(131, 13, 'Patriotas americanos', 'Victoria', 'Ejércitos independentistas hispanoamericanos.'),
(132, 13, 'Imperio español', 'Derrota', 'Fuerzas realistas españolas.'),
(141, 14, 'Reino Unido', 'Victoria', 'Marina y ejército británicos.'),
(142, 14, 'Dinastía Qing', 'Derrota', 'Imperio chino de la dinastía Qing.'),
(151, 15, 'Aliados', 'Victoria', 'Francia, Reino Unido y Imperio otomano.'),
(152, 15, 'Imperio ruso', 'Derrota', 'Ejército imperial ruso.'),
(161, 16, 'Unión', 'Victoria', 'Estados Unidos de América.'),
(162, 16, 'Confederación', 'Derrota', 'Estados Confederados de América.'),
(171, 17, 'Chile', 'Victoria', 'Ejército y marina de Chile.'),
(172, 17, 'Perú y Bolivia', 'Derrota', 'Alianza peruano-boliviana.'),
(181, 18, 'Reino Unido', 'Victoria', 'Imperio británico.'),
(182, 18, 'Repúblicas bóeres', 'Derrota', 'Transvaal y Estado Libre de Orange.'),
(191, 19, 'Imperio ruso', 'Derrota', 'Ejército y flota imperiales rusos.'),
(192, 19, 'Imperio del Japón', 'Victoria', 'Ejército y Armada Imperial Japonesa.'),
(201, 20, 'Aliados', 'Victoria', 'Reino Unido, Francia, Rusia, Italia, Estados Unidos, Serbia y Japón.'),
(202, 20, 'Potencias Centrales', 'Derrota', 'Alemania, Austria-Hungría y Imperio otomano.'),
(211, 21, 'Paraguay', 'Victoria', 'Ejército paraguayo.'),
(212, 21, 'Bolivia', 'Derrota', 'Ejército boliviano.'),
(221, 22, 'Aliados', 'Victoria', 'Reino Unido, Unión Soviética, Estados Unidos, China y sus aliados.'),
(222, 22, 'Eje', 'Derrota', 'Alemania, Italia y Japón.'),
(231, 23, 'Corea del Sur y la ONU', 'Indeciso', 'Corea del Sur, Estados Unidos y fuerzas de la ONU.'),
(232, 23, 'Corea del Norte y China', 'Indeciso', 'Corea del Norte, China y apoyo soviético.'),
(241, 24, 'Francia', 'Derrota', 'Ejército francés y colonial.'),
(242, 24, 'FLN argelino', 'Victoria', 'Frente de Liberación Nacional.'),
(251, 25, 'Vietnam del Norte y el Viet Cong', 'Victoria', 'Fuerzas comunistas norvietnamitas y guerrillas del sur.'),
(252, 25, 'Vietnam del Sur y sus aliados', 'Derrota', 'Vietnam del Sur, Estados Unidos, Corea del Sur y Australia.'),
(261, 26, 'Israel', 'Victoria', 'Fuerzas de Defensa de Israel.'),
(262, 26, 'Egipto, Siria y Jordania', 'Derrota', 'Coalición árabe.'),
(271, 27, 'Israel', 'Victoria', 'Fuerzas de Defensa de Israel.'),
(272, 27, 'Egipto y Siria', 'Derrota', 'Coalición árabe.'),
(281, 28, 'Reino Unido', 'Victoria', 'Fuerza de Tareas británica.'),
(282, 28, 'Argentina', 'Derrota', 'Fuerzas Armadas argentinas.'),
(291, 29, 'Coalición internacional', 'Victoria', 'Estados Unidos, Reino Unido, Francia, Egipto y Arabia Saudita, entre otros.'),
(292, 29, 'Irak', 'Derrota', 'Ejército iraquí.'),
(301, 30, 'Serbia y el Ejército Federal', 'Derrota', 'República Federal de Yugoslavia y Serbia.'),
(302, 30, 'Repúblicas secesionistas y la OTAN', 'Victoria', 'Croacia, Bosnia y Herzegovina, Eslovenia y la OTAN.'),
(311, 31, 'Coalición liderada por Estados Unidos', 'Derrota', 'Estados Unidos, Reino Unido, Canadá y Australia, entre otros.'),
(312, 31, 'Talibán', 'Victoria', 'Emirato Islámico de Afganistán.'),
(321, 32, 'Coalición liderada por Estados Unidos', 'Victoria', 'Estados Unidos, Reino Unido y Australia.'),
(322, 32, 'Irak', 'Derrota', 'Régimen de Sadam Huseín.'),
(331, 33, 'Gobierno sirio y aliados', 'Indeciso', 'Régimen de Al Asad, Rusia e Irán.'),
(332, 33, 'Oposición siria', 'Indeciso', 'Coalición de grupos opositores.'),
(341, 34, 'Ucrania', 'En curso', 'Fuerzas Armadas de Ucrania.'),
(342, 34, 'Rusia', 'En curso', 'Fuerzas Armadas de la Federación de Rusia.');

-- ----------------------------------------------------------------------------
-- Participaciones de países
-- Columnas: id_guerra, id_pais, id_bando, tropas (aprox.), bajas (muertes aprox.)
-- ----------------------------------------------------------------------------
INSERT INTO participaciones (id_guerra, id_pais, id_bando, tropas, bajas) VALUES
-- 1. Guerras Médicas
(1, 3, 11, NULL, NULL),          -- Atenas
(1, 4, 11, NULL, NULL),          -- Esparta
(1, 2, 12, NULL, NULL),          -- Imperio Persa
-- 2. Guerra del Peloponeso
(2, 4, 21, NULL, NULL),          -- Esparta
(2, 3, 22, NULL, NULL),          -- Atenas
-- 3. Alejandro Magno
(3, 5, 31, 40000, NULL),         -- Macedonia
(3, 2, 32, 100000, NULL),        -- Imperio Persa
-- 4. Guerras Púnicas
(4, 6, 41, NULL, NULL),          -- Roma
(4, 7, 42, NULL, NULL),          -- Cartago
-- 5. Guerra de las Galias
(5, 6, 51, 60000, NULL),         -- Roma
(5, 8, 52, NULL, NULL),          -- Galia
-- 6. Guerra de los Cien Años
(6, 9, 61, NULL, NULL),          -- Inglaterra
(6, 10, 62, NULL, NULL),         -- Francia
-- 7. Guerras Italianas
(7, 24, 71, NULL, NULL),         -- Francia
(7, 11, 72, NULL, NULL),         -- Imperio español
(7, 13, 72, NULL, NULL),         -- Sacro Imperio
-- 8. Guerra de los Treinta Años
(8, 11, 81, NULL, NULL),         -- Imperio español
(8, 13, 81, NULL, NULL),         -- Sacro Imperio
(8, 12, 82, NULL, NULL),         -- Provincias Unidas
(8, 62, 82, NULL, NULL),         -- Suecia
(8, 63, 82, NULL, NULL),         -- Dinamarca
-- 9. Guerra de Sucesión Española
(9, 10, 91, NULL, NULL),         -- Reino de Francia
(9, 11, 91, NULL, NULL),         -- Imperio español
(9, 9, 92, NULL, NULL),          -- Reino de Inglaterra
(9, 12, 92, NULL, NULL),         -- Provincias Unidas
(9, 52, 92, NULL, NULL),         -- Austria
-- 10. Guerra de los Siete Años
(10, 23, 101, NULL, NULL),       -- Reino Unido
(10, 14, 101, NULL, NULL),       -- Prusia
(10, 10, 102, NULL, NULL),       -- Reino de Francia
(10, 52, 102, NULL, NULL),       -- Austria
(10, 15, 102, NULL, NULL),       -- Imperio ruso
-- 11. Independencia de Estados Unidos
(11, 28, 111, 25000, NULL),      -- Estados Unidos
(11, 24, 111, NULL, NULL),       -- Francia
(11, 11, 111, NULL, NULL),       -- España
(11, 23, 112, NULL, NULL),       -- Reino Unido
-- 12. Guerras Napoleónicas
(12, 23, 121, NULL, NULL),       -- Reino Unido
(12, 14, 121, NULL, NULL),       -- Prusia
(12, 15, 121, NULL, NULL),       -- Imperio ruso
(12, 52, 121, NULL, NULL),       -- Austria
(12, 35, 121, NULL, NULL),       -- España
(12, 24, 122, NULL, NULL),       -- Francia
-- 13. Independencia Hispanoamericana
(13, 34, 131, NULL, NULL),       -- Argentina
(13, 58, 131, NULL, NULL),       -- México
(13, 59, 131, NULL, NULL),       -- Colombia
(13, 60, 131, NULL, NULL),       -- Venezuela
(13, 36, 131, NULL, NULL),       -- Chile
(13, 37, 131, NULL, NULL),       -- Perú
(13, 38, 131, NULL, NULL),       -- Bolivia
(13, 61, 131, NULL, NULL),       -- Ecuador
(13, 11, 132, NULL, NULL),       -- Imperio español
-- 14. Primera Guerra del Opio
(14, 23, 141, NULL, NULL),       -- Reino Unido
(14, 30, 142, NULL, NULL),       -- China
-- 15. Guerra de Crimea
(15, 24, 151, NULL, NULL),       -- Francia
(15, 23, 151, NULL, NULL),       -- Reino Unido
(15, 17, 151, NULL, NULL),       -- Imperio otomano
(15, 15, 152, NULL, NULL),       -- Imperio ruso
-- 16. Guerra de Secesión
(16, 28, 161, NULL, NULL),       -- Unión
(16, 21, 162, NULL, NULL),       -- Confederación
-- 17. Guerra del Pacífico
(17, 36, 171, NULL, NULL),       -- Chile
(17, 37, 172, NULL, NULL),       -- Perú
(17, 38, 172, NULL, NULL),       -- Bolivia
-- 18. Guerra de los Bóeres
(18, 23, 181, NULL, NULL),       -- Reino Unido
(18, 22, 182, NULL, NULL),       -- Repúblicas bóeres
-- 19. Guerra Ruso-Japonesa
(19, 15, 191, NULL, NULL),       -- Imperio ruso
(19, 29, 192, NULL, NULL),       -- Japón
-- 20. Primera Guerra Mundial
(20, 23, 201, 8900000, 1000000), -- Reino Unido
(20, 24, 201, 8500000, 1400000), -- Francia
(20, 15, 201, 12000000, 1800000),-- Imperio ruso
(20, 26, 201, 5500000, 650000),  -- Italia
(20, 28, 201, 4700000, 116000),  -- Estados Unidos
(20, 41, 201, 700000, 450000),   -- Serbia
(20, 29, 201, 800000, 415),      -- Japón
(20, 25, 202, 13200000, 2000000),-- Alemania
(20, 16, 202, 7800000, 1100000), -- Austria-Hungría
(20, 17, 202, 3000000, 770000),  -- Imperio otomano
-- 21. Guerra del Chaco
(21, 69, 211, NULL, NULL),       -- Paraguay
(21, 38, 212, NULL, NULL),       -- Bolivia
-- 22. Segunda Guerra Mundial
(22, 23, 221, 5900000, 450000),  -- Reino Unido
(22, 18, 221, 34000000, 27000000),-- Unión Soviética
(22, 28, 221, 16000000, 418000), -- Estados Unidos
(22, 24, 221, 1200000, 600000),  -- Francia
(22, 30, 221, 14000000, 20000000),-- China
(22, 54, 221, 1100000, 45000),   -- Canadá
(22, 55, 221, 1000000, 40000),   -- Australia
(22, 56, 221, 2500000, 2000000), -- India
(22, 25, 222, 18000000, 5300000),-- Alemania
(22, 26, 222, 4500000, 450000),  -- Italia
(22, 29, 222, 9000000, 2500000), -- Japón
-- 23. Guerra de Corea
(23, 32, 231, 600000, 200000),   -- Corea del Sur
(23, 28, 231, 300000, 36000),    -- Estados Unidos
(23, 23, 231, 100000, 1000),     -- Reino Unido
(23, 31, 232, 260000, 500000),   -- Corea del Norte
(23, 30, 232, 1000000, 400000),  -- China
-- 24. Guerra de Argelia
(24, 24, 241, 400000, 25000),    -- Francia
(24, 67, 242, NULL, NULL),       -- Argelia
-- 25. Guerra de Vietnam
(25, 19, 251, NULL, 1100000),    -- Vietnam del Norte
(25, 18, 251, NULL, NULL),       -- Unión Soviética
(25, 30, 251, NULL, NULL),       -- China
(25, 20, 252, NULL, 250000),     -- Vietnam del Sur
(25, 28, 252, 2700000, 58000),   -- Estados Unidos
(25, 32, 252, 300000, 5000),     -- Corea del Sur
(25, 55, 252, 60000, 500),       -- Australia
-- 26. Guerra de los Seis Días
(26, 46, 261, NULL, NULL),       -- Israel
(26, 47, 262, NULL, NULL),       -- Egipto
(26, 48, 262, NULL, NULL),       -- Siria
(26, 64, 262, NULL, NULL),       -- Jordania
-- 27. Guerra de Yom Kipur
(27, 46, 271, NULL, NULL),       -- Israel
(27, 47, 272, NULL, NULL),       -- Egipto
(27, 48, 272, NULL, NULL),       -- Siria
-- 28. Guerra de las Malvinas
(28, 23, 281, 28000, 255),       -- Reino Unido
(28, 34, 282, 12000, 649),       -- Argentina
-- 29. Guerra del Golfo
(29, 28, 291, 700000, 294),      -- Estados Unidos
(29, 23, 291, 53000, 47),        -- Reino Unido
(29, 24, 291, 18000, 2),         -- Francia
(29, 47, 291, 35000, 0),         -- Egipto
(29, 65, 291, 100000, 0),        -- Arabia Saudita
(29, 39, 292, NULL, 20000),      -- Irak
-- 30. Guerras Yugoslavas
(30, 41, 301, NULL, NULL),       -- Serbia
(30, 42, 302, NULL, NULL),       -- Croacia
(30, 43, 302, NULL, NULL),       -- Bosnia y Herzegovina
(30, 66, 302, NULL, NULL),       -- Eslovenia
(30, 28, 302, NULL, NULL),       -- Estados Unidos / OTAN
-- 31. Guerra de Afganistán
(31, 28, 311, NULL, 2400),       -- Estados Unidos
(31, 23, 311, NULL, 457),        -- Reino Unido
(31, 54, 311, NULL, 158),        -- Canadá
(31, 55, 311, NULL, 41),         -- Australia
(31, 44, 312, NULL, NULL),       -- Afganistán / Talibán
-- 32. Guerra de Irak
(32, 28, 321, 150000, 4500),     -- Estados Unidos
(32, 23, 321, 45000, 179),       -- Reino Unido
(32, 55, 321, 2000, NULL),       -- Australia
(32, 39, 322, NULL, NULL),       -- Irak
-- 33. Guerra civil siria
(33, 48, 331, NULL, 100000),     -- Siria
(33, 27, 331, NULL, NULL),       -- Rusia
(33, 68, 331, NULL, NULL),       -- Irán
(33, 70, 332, NULL, NULL),       -- Oposición siria
-- 34. Invasión rusa de Ucrania
(34, 45, 341, NULL, NULL),       -- Ucrania
(34, 27, 342, NULL, NULL);       -- Rusia

-- ----------------------------------------------------------------------------
-- Batallas destacadas
-- ----------------------------------------------------------------------------
INSERT INTO batallas (id_guerra, nombre, anio, fecha, lugar, resultado, descripcion) VALUES
(1, 'Batalla de Maratón', -490, NULL, 'Maratón, Grecia', 'Victoria griega', 'Atenas y Platea detuvieron la primera invasión persa.'),
(1, 'Batalla de Salamina', -480, NULL, 'Golfo Sarónico', 'Victoria griega', 'La flota griega derrotó a la persa en el mar.'),
(1, 'Batalla de Platea', -479, NULL, 'Beocia', 'Victoria griega', 'Derrota definitiva del ejército persa en Grecia.'),
(2, 'Batalla de Egospótamos', -405, NULL, 'Helesponto', 'Victoria espartana', 'La flota espartana destruyó la ateniense y decidió la guerra.'),
(3, 'Batalla de Issos', -333, NULL, 'Cilicia', 'Victoria macedonia', 'Alejandro derrotó a Darío III.'),
(3, 'Batalla de Gaugamela', -331, NULL, 'Mesopotamia', 'Victoria macedonia', 'Alejandro venció al último gran ejército persa.'),
(4, 'Batalla de Cannas', -216, NULL, 'Apulia, Italia', 'Victoria cartaginesa', 'Aníbal aniquiló a un ejército romano.'),
(4, 'Batalla de Zama', -202, NULL, 'Numidia', 'Victoria romana', 'Escipión derrotó a Aníbal y puso fin a la Segunda Guerra Púnica.'),
(5, 'Batalla de Alesia', -52, NULL, 'Galia', 'Victoria romana', 'César sometió a Vercingétorix.'),
(6, 'Batalla de Agincourt', 1415, '1415-10-25', 'Agincourt, Francia', 'Victoria inglesa', 'Los arqueros ingleses derrotaron a la caballería francesa.'),
(6, 'Batalla de Castillon', 1453, '1453-07-17', 'Castillon, Francia', 'Victoria francesa', 'Última gran batalla de la Guerra de los Cien Años.'),
(7, 'Batalla de Pavía', 1525, '1525-02-24', 'Pavía, Italia', 'Victoria española', 'Captura de Francisco I de Francia.'),
(8, 'Batalla de Lutzen', 1632, '1632-11-16', 'Lutzen, Sajonia', 'Victoria protestante', 'Gustavo II Adolfo murió en combate.'),
(8, 'Batalla de Rocroi', 1643, '1643-05-19', 'Rocroi, Francia', 'Victoria francesa', 'Fin de la supremacía militar española en Europa.'),
(9, 'Batalla de Blenheim', 1704, '1704-08-13', 'Blenheim, Baviera', 'Victoria de la Gran Alianza', 'Marlborough y Eugenio de Saboya derrotaron a Francia y Baviera.'),
(9, 'Batalla de Malplaquet', 1709, '1709-09-11', 'Malplaquet, Francia', 'Victoria pírrica de la Alianza', 'Una de las batallas más sangrientas del siglo XVIII.'),
(10, 'Batalla de Plassey', 1757, '1757-06-23', 'Bengala, India', 'Victoria británica', 'La Compañía Británica de las Indias Orientales consolidó su poder en India.'),
(10, 'Batalla de Quebec', 1759, '1759-09-13', 'Quebec, Canadá', 'Victoria británica', 'La caída de Quebec decidió el dominio británico en Canadá.'),
(11, 'Batalla de Saratoga', 1777, '1777-10-17', 'Nueva York', 'Victoria estadounidense', 'Convenció a Francia de apoyar la independencia.'),
(11, 'Batalla de Yorktown', 1781, '1781-10-19', 'Virginia', 'Victoria estadounidense', 'Rendición de Cornwallis y fin efectivo de la guerra.'),
(12, 'Batalla de Austerlitz', 1805, '1805-12-02', 'Moravia', 'Victoria francesa', 'La mayor victoria de Napoleón.'),
(12, 'Batalla de Borodino', 1812, '1812-09-07', 'Borodino, Rusia', 'Victoria francesa pírrica', 'Antesala de la ocupación y el incendio de Moscú.'),
(12, 'Batalla de Waterloo', 1815, '1815-06-18', 'Bélgica', 'Victoria de la coalición', 'Derrota final de Napoleón.'),
(13, 'Batalla de Boyacá', 1819, '1819-08-07', 'Colombia', 'Victoria independentista', 'Consolidó la independencia de Nueva Granada.'),
(13, 'Batalla de Ayacucho', 1824, '1824-12-09', 'Perú', 'Victoria independentista', 'Fin de la dominación española en Sudamérica continental.'),
(14, 'Batalla de Cantón', 1841, '1841-05-21', 'Cantón, China', 'Victoria británica', 'Demostró la superioridad naval británica.'),
(15, 'Batalla de Balaclava', 1854, '1854-10-25', 'Crimea', 'Indecisa', 'Conocida por la carga de la Brigada Ligera.'),
(15, 'Sitio de Sebastopol', 1855, '1855-09-08', 'Crimea', 'Victoria aliada', 'Caída de la principal base naval rusa.'),
(16, 'Batalla de Antietam', 1862, '1862-09-17', 'Maryland', 'Indecisa', 'El día más sangriento de la historia militar estadounidense.'),
(16, 'Batalla de Gettysburg', 1863, '1863-07-01', 'Pensilvania', 'Victoria de la Unión', 'Punto de inflexión de la Guerra de Secesión.'),
(17, 'Combate de Iquique', 1879, '1879-05-21', 'Iquique, Chile', 'Victoria peruana', 'Muerte de Arturo Prat; hundimiento de la Esmeralda.'),
(17, 'Combate de Angamos', 1879, '1879-10-08', 'Angamos, Perú', 'Victoria chilena', 'Captura del monitor Huáscar y de Miguel Grau.'),
(17, 'Batalla de Lima', 1881, '1881-01-15', 'Lima, Perú', 'Victoria chilena', 'Ocupación de la capital peruana.'),
(18, 'Sitio de Ladysmith', 1899, '1899-11-02', 'Ladysmith, Sudáfrica', 'Victoria británica', 'Sitio y liberación de la guarnición británica.'),
(18, 'Batalla de Paardeberg', 1900, '1900-02-27', 'Río Modder, Sudáfrica', 'Victoria británica', 'Rendición de una importante fuerza bóer.'),
(19, 'Sitio de Port Arthur', 1904, '1904-08-01', 'Manchuria', 'Victoria japonesa', 'Caída de la base naval rusa.'),
(19, 'Batalla de Tsushima', 1905, '1905-05-27', 'Estrecho de Tsushima', 'Victoria japonesa', 'Destrucción de la flota rusa del Báltico.'),
(20, 'Primera Batalla del Marne', 1914, '1914-09-05', 'Francia', 'Victoria aliada', 'Detuvo la ofensiva alemana sobre París.'),
(20, 'Batalla de Verdún', 1916, '1916-02-21', 'Verdún, Francia', 'Indecisa', 'Diez meses de desgaste extremo.'),
(20, 'Batalla del Somme', 1916, '1916-07-01', 'Somme, Francia', 'Indecisa', 'Ofensiva británica con enormes pérdidas.'),
(21, 'Batalla de Boquerón', 1932, '1932-09-09', 'Chaco Boreal', 'Victoria paraguaya', 'Primera gran batalla de la Guerra del Chaco.'),
(22, 'Batalla de Midway', 1942, '1942-06-04', 'Pacífico central', 'Victoria estadounidense', 'Punto de inflexión en el Pacífico.'),
(22, 'Batalla de Stalingrado', 1942, '1942-08-23', 'Stalingrado, URSS', 'Victoria soviética', 'Rendición del 6.º Ejército alemán.'),
(22, 'Desembarco de Normandía', 1944, '1944-06-06', 'Normandía, Francia', 'Victoria aliada', 'Apertura del frente occidental.'),
(22, 'Batalla de Berlín', 1945, '1945-04-16', 'Berlín, Alemania', 'Victoria soviética', 'Última gran ofensiva en Europa.'),
(23, 'Desembarco de Inchon', 1950, '1950-09-15', 'Inchon, Corea', 'Victoria de la ONU', 'Contraofensiva que revirtió la situación inicial.'),
(23, 'Batalla del embalse de Chosin', 1950, '1950-11-27', 'Corea del Norte', 'Retirada de la ONU', 'Intervención china y repliegue de las fuerzas de la ONU.'),
(24, 'Batalla de Argel', 1957, '1957-01-07', 'Argel, Argelia', 'Victoria francesa táctica', 'Represión de la insurgencia urbana del FLN.'),
(25, 'Batalla de Ap Bac', 1963, '1963-01-02', 'Vietnam del Sur', 'Victoria del Viet Cong', 'Reveló las dificultades del ejército survietnamita.'),
(25, 'Ofensiva del Tet', 1968, '1968-01-30', 'Vietnam del Sur', 'Victoria táctica estadounidense', 'Gran impacto político y mediático contra la guerra.'),
(25, 'Batalla de Khe Sanh', 1968, '1968-01-21', 'Vietnam del Sur', 'Victoria estadounidense', 'Sitio prolongado durante la ofensiva del Tet.'),
(26, 'Operación Moked', 1967, '1967-06-05', 'Oriente Medio', 'Victoria israelí', 'Ataque preventivo que destruyó la aviación árabe.'),
(26, 'Batalla de los Altos del Golán', 1967, '1967-06-09', 'Altos del Golán', 'Victoria israelí', 'Conquista del territorio sirio.'),
(27, 'Travesía del Canal de Suez', 1973, '1973-10-06', 'Canal de Suez', 'Victoria egipcia inicial', 'Ofensiva sorpresa egipcia al inicio de la guerra.'),
(27, 'Batalla de los Altos del Golán', 1973, '1973-10-06', 'Altos del Golán', 'Victoria israelí', 'Contraofensiva israelí tras la sorpresa inicial.'),
(28, 'Desembarco de San Carlos', 1982, '1982-05-21', 'Islas Malvinas', 'Victoria británica', 'Establecimiento de la cabeza de playa británica.'),
(28, 'Batalla de Goose Green', 1982, '1982-05-28', 'Islas Malvinas', 'Victoria británica', 'Primera gran batalla terrestre del conflicto.'),
(29, 'Batalla de Khafji', 1991, '1991-01-29', 'Arabia Saudita', 'Victoria de la coalición', 'Última ofensiva iraquí antes de la campaña terrestre.'),
(29, 'Operación Tormenta del Desierto', 1991, '1991-02-24', 'Kuwait e Irak', 'Victoria de la coalición', 'Ofensiva terrestre que expulsó a Irak de Kuwait.'),
(30, 'Sitio de Sarajevo', 1992, '1992-04-05', 'Sarajevo, Bosnia', 'Asedio prolongado', 'Uno de los sitios más largos de la historia moderna.'),
(30, 'Operación Tormenta', 1995, '1995-08-04', 'Croacia', 'Victoria croata', 'Ofensiva que puso fin a la guerra en Croacia.'),
(31, 'Batalla de Tora Bora', 2001, '2001-12-12', 'Afganistán', 'Victoria de la coalición', 'Ofensiva contra refugios de Al Qaeda.'),
(31, 'Operación Moshtarak', 2010, '2010-02-13', 'Helmand, Afganistán', 'Indecisa', 'Gran ofensiva contra el Talibán en Helmand.'),
(32, 'Batalla de Bagdad', 2003, '2003-04-03', 'Bagdad, Irak', 'Victoria de la coalición', 'Caída de la capital iraquí.'),
(32, 'Segunda Batalla de Faluya', 2004, '2004-11-07', 'Faluya, Irak', 'Victoria de la coalición', 'Ofensiva contra la insurgencia suní.'),
(33, 'Batalla de Alepo', 2012, '2012-07-19', 'Alepo, Siria', 'Victoria del gobierno sirio', 'Punto central del conflicto sirio.'),
(33, 'Ofensiva de Guta Oriental', 2018, '2018-02-18', 'Guta Oriental, Siria', 'Victoria del gobierno sirio', 'Reconquista del último bastión rebelde cerca de Damasco.'),
(34, 'Batalla de Kiev', 2022, '2022-02-24', 'Kiev, Ucrania', 'Victoria ucraniana', 'Fracaso de la ofensiva rusa sobre la capital.'),
(34, 'Batalla de Mariúpol', 2022, '2022-02-24', 'Mariúpol, Ucrania', 'Victoria rusa', 'Asedio y destrucción de la ciudad portuaria.'),
(34, 'Batalla de Bajmut', 2022, '2022-08-01', 'Bajmut, Ucrania', 'Victoria rusa', 'Combate urbano prolongado de alto desgaste.');

-- ----------------------------------------------------------------------------
-- Tratados y acuerdos
-- ----------------------------------------------------------------------------
INSERT INTO tratados (id_guerra, nombre, anio, lugar, descripcion) VALUES
(1, 'Paz de Calias', -449, 'Susa', 'Puso fin a las Guerras Médicas.'),
(4, 'Tratado de paz de 201 a.C.', -201, 'Cartago', 'Fin de la Segunda Guerra Púnica y pérdida del imperio cartaginés.'),
(7, 'Paz de Cateau-Cambrésis', 1559, 'Cateau-Cambrésis', 'Fin de las Guerras Italianas y hegemonía española en Italia.'),
(8, 'Paz de Westfalia', 1648, 'Münster y Osnabrück', 'Reconoció la libertad religiosa de los príncipes y el nuevo equilibrio europeo.'),
(9, 'Tratado de Utrecht', 1713, 'Utrecht', 'Reconoció a Felipe V como rey de España y cedió territorios a Austria y Gran Bretaña.'),
(10, 'Tratado de París', 1763, 'París', 'Francia cedió Canadá y territorios de la India a Gran Bretaña.'),
(10, 'Tratado de Hubertusburgo', 1763, 'Hubertusburgo', 'Prusia consolidó su control sobre Silesia.'),
(11, 'Tratado de París', 1783, 'París', 'Gran Bretaña reconoció la independencia de Estados Unidos.'),
(12, 'Congreso de Viena', 1815, 'Viena', 'Reordenó Europa tras la derrota de Napoleón.'),
(13, 'Capitulación de Ayacucho', 1824, 'Ayacucho', 'Fin de la dominación española en Sudamérica continental.'),
(14, 'Tratado de Nankín', 1842, 'Nankín', 'China cedió Hong Kong y abrió varios puertos al comercio británico.'),
(15, 'Tratado de París', 1856, 'París', 'Fin de la Guerra de Crimea; neutralización del mar Negro.'),
(16, 'Capitulación de Appomattox', 1865, 'Appomattox', 'Rendición del general Lee y fin efectivo de la guerra.'),
(17, 'Tratado de Ancón', 1883, 'Lima', 'Chile y Perú firmaron la paz; Perú cedió Tarapacá.'),
(18, 'Tratado de Vereeniging', 1902, 'Vereeniging', 'Fin de la Guerra de los Bóeres e incorporación al Imperio británico.'),
(19, 'Tratado de Portsmouth', 1905, 'Portsmouth', 'Mediación de Estados Unidos; Japón consolidó su influencia en Corea y Manchuria.'),
(20, 'Tratado de Brest-Litovsk', 1918, 'Brest-Litovsk', 'Rusia soviética salió de la guerra y cedió amplios territorios.'),
(20, 'Tratado de Versalles', 1919, 'Versalles', 'Impulsó reparaciones y sanciones a Alemania.'),
(20, 'Tratado de Lausana', 1923, 'Lausana', 'Reordenó las fronteras del Imperio otomano y reconoció a Turquía.'),
(21, 'Tratado de Paz, Amistad y Límites', 1938, 'Buenos Aires', 'Delimitó la frontera entre Paraguay y Bolivia.'),
(22, 'Acta de Rendición de Alemania', 1945, 'Berlín', 'Rendición incondicional del Tercer Reich.'),
(22, 'Tratado de San Francisco', 1951, 'San Francisco', 'Tratado de paz con Japón y fin formal de la guerra en Asia.'),
(23, 'Armisticio de Panmunjom', 1953, 'Panmunjom', 'Alto el fuego sin tratado de paz definitivo.'),
(24, 'Acuerdos de Évian', 1962, 'Évian-les-Bains', 'Reconocimiento de la independencia de Argelia.'),
(25, 'Acuerdos de Paz de París', 1973, 'París', 'Estados Unidos se retiró de Vietnam; el conflicto continuó hasta 1975.'),
(26, 'Resolución 242 del Consejo de Seguridad', 1967, 'Nueva York', 'Exigió la retirada israelí de los territorios ocupados.'),
(27, 'Resolución 338 del Consejo de Seguridad', 1973, 'Nueva York', 'Alto el fuego entre Israel, Egipto y Siria.'),
(29, 'Resolución 687 del Consejo de Seguridad', 1991, 'Nueva York', 'Condiciones para el alto el fuego con Irak.'),
(30, 'Acuerdos de Dayton', 1995, 'Dayton', 'Fin de la guerra de Bosnia y nuevo ordenamiento institucional.'),
(30, 'Acuerdo de Kumanovo', 1999, 'Kumanovo', 'Retirada serbia de Kosovo y despliegue de la OTAN.'),
(31, 'Acuerdo de Doha', 2020, 'Doha', 'Acuerdo entre Estados Unidos y el Talibán previo a la retirada de 2021.');

-- ============================================================================
-- VISTAS DE CONSULTA
-- ============================================================================

CREATE VIEW vw_guerras_detalle AS
SELECT
    g.id_guerra,
    g.nombre,
    g.anio_inicio,
    g.anio_fin,
    g.fecha_inicio,
    g.fecha_fin,
    g.siglo,
    g.id_tipo,
    t.nombre AS tipo,
    g.id_region,
    r.nombre AS region,
    r.continente,
    g.lugar,
    g.resultado,
    g.bajas_totales,
    g.descripcion,
    (SELECT COUNT(*) FROM participaciones p WHERE p.id_guerra = g.id_guerra) AS num_paises,
    (SELECT COUNT(*) FROM batallas b WHERE b.id_guerra = g.id_guerra) AS num_batallas,
    (SELECT COUNT(*) FROM tratados tr WHERE tr.id_guerra = g.id_guerra) AS num_tratados
FROM guerras g
INNER JOIN tipos_guerra t ON t.id_tipo = g.id_tipo
INNER JOIN regiones r ON r.id_region = g.id_region;

CREATE VIEW vw_bandos_participantes AS
SELECT
    g.id_guerra,
    g.nombre AS guerra,
    g.siglo,
    b.id_bando,
    b.nombre AS bando,
    b.resultado AS resultado_bando,
    p.id_pais,
    p.nombre AS pais,
    pa.tropas,
    pa.bajas
FROM guerras g
INNER JOIN bandos b ON b.id_guerra = g.id_guerra
INNER JOIN participaciones pa ON pa.id_bando = b.id_bando
INNER JOIN paises p ON p.id_pais = pa.id_pais;

CREATE VIEW vw_resumen_siglo AS
SELECT
    siglo,
    COUNT(*) AS total_guerras,
    SUM(COALESCE(bajas_totales, 0)) AS bajas_registradas,
    ROUND(AVG(bajas_totales), 0) AS promedio_bajas,
    MIN(anio_inicio) AS primer_anio
FROM guerras
GROUP BY siglo
ORDER BY primer_anio;

CREATE VIEW vw_resumen_region AS
SELECT
    r.id_region,
    r.nombre AS region,
    r.continente,
    COUNT(g.id_guerra) AS total_guerras,
    SUM(COALESCE(g.bajas_totales, 0)) AS bajas_registradas,
    ROUND(AVG(g.bajas_totales), 0) AS promedio_bajas
FROM regiones r
LEFT JOIN guerras g ON g.id_region = r.id_region
GROUP BY r.id_region, r.nombre, r.continente;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
