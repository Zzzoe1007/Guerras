# Catálogo de Guerras de la Historia

Proyecto final de bases de datos: catálogo relacional de conflictos históricos con backend en Python y MySQL. Permite consultar, registrar, actualizar y eliminar guerras, además de generar reportes por siglo, región, tipo, bando y país.

Incluye **dos interfaces** que comparten la misma base de datos, el mismo repositorio y los mismos reportes:

- Una **interfaz web con estética de enciclopedia** (Flask + Jinja2), pensada para presentar el proyecto.
- Una **aplicación de consola** completa, útil como alternativa ligera.

**Requisitos del profesor cubiertos**

- Base de datos relacional en MySQL/phpMyAdmin con claves primarias y foráneas.
- Script SQL completo listo para importar, con datos históricos reales.
- Backend Python con conexión a MySQL, CRUD y consultas avanzadas.
- Instrucciones de instalación y ejecución.

---

## 1. Inicio rápido

```bash
# 1. Crear e importar la base de datos (phpMyAdmin o consola)
mysql -u root -p < sql/catalogo_guerras.sql

# 2. Instalar las dependencias
python -m pip install -r requirements.txt

# 3. Configurar credenciales (ejemplo XAMPP: root sin contraseña)
export DB_USER=root
export DB_PASSWORD=

# 4. Interfaz web (recomendada para la presentación)
python run_web.py
# Abrir http://127.0.0.1:5000/

# 5. Aplicación de consola (alternativa)
python main.py
```

Demostración no interactiva (útil para comprobar la conexión y los reportes):

```bash
python main.py --demo
```

---

## 2. Estructura del proyecto

```text
Guerra/
├── main.py                        # Aplicación de consola
├── run_web.py                     # Servidor de la interfaz web
├── requirements.txt               # mysql-connector-python + Flask
├── README.md
├── app/
│   ├── __init__.py
│   ├── config.py                  # Configuración por variables de entorno
│   ├── db.py                      # Conexión, cursor y transacciones
│   ├── errores.py                 # Excepciones de negocio
│   ├── repositorio.py             # CRUD y validaciones
│   ├── reportes.py                # Consultas avanzadas
│   ├── ui.py                      # Tablas ASCII y entradas de usuario
│   ├── web.py                     # Rutas, CSRF y errores de la interfaz web
│   ├── templates/                 # Plantillas Jinja2 (estilo enciclopedia)
│   │   ├── _macros.html
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── buscar.html
│   │   ├── guerras.html
│   │   ├── guerra.html
│   │   ├── formulario.html
│   │   ├── eliminar.html
│   │   ├── reportes.html
│   │   ├── pais.html
│   │   ├── ayuda.html
│   │   ├── error.html
│   │   └── 404.html
│   └── static/
│       ├── css/estilos.css        # Diseño completo, sin CDNs
│       ├── js/app.js              # Menú móvil, impresión y atajo de búsqueda
│       └── img/                   # Logo, emblema y portada en SVG
└── sql/
    ├── catalogo_guerras.sql       # Esquema + datos + vistas (importar este)
    └── consultas_avanzadas.sql    # 15 consultas de reporte para phpMyAdmin
```

---

## 3. Base de datos

### 3.1 Importar en phpMyAdmin

1. Abra phpMyAdmin (`http://localhost/phpmyadmin`).
2. Vaya a **Importar**.
3. Seleccione el archivo `sql/catalogo_guerras.sql`.
4. Formato: **SQL**, conjunto de caracteres **utf-8**.
5. Pulse **Continuar**.

El script crea la base `catalogo_guerras`, las tablas, las vistas y carga los datos de prueba. Se puede volver a importar: elimina y recrea únicamente los objetos de este proyecto.

### 3.2 Modelo relacional

```text
regiones 1 ──── N guerras N ──── 1 tipos_guerra
                   │
                   ├── 1 ──── N bandos 1 ──── N participaciones N ──── 1 paises
                   ├── 1 ──── N batallas
                   └── 1 ──── N tratados
```

| Tabla | Función | Claves |
|---|---|---|
| `regiones` | Región geográfica del conflicto | PK `id_region` |
| `tipos_guerra` | Clasificación (mundial, civil, conquista...) | PK `id_tipo` |
| `paises` | Países y entidades históricas | PK `id_pais`, UNIQUE `nombre` |
| `guerras` | Entidad principal del catálogo | PK `id_guerra`, FK `id_tipo`, FK `id_region`, UNIQUE `nombre` |
| `bandos` | Bandos de cada guerra y su resultado | PK `id_bando`, FK `id_guerra`, UNIQUE (`id_guerra`, `nombre`) |
| `participaciones` | Países que lucharon en cada bando | PK propia, FK compuesta (`id_bando`, `id_guerra`), FK `id_pais`, UNIQUE (`id_guerra`, `id_pais`) |
| `batallas` | Batallas destacadas | PK `id_batalla`, FK `id_guerra` |
| `tratados` | Tratados y acuerdos de paz | PK `id_tratado`, FK `id_guerra` |

Características del diseño:

- Tercera forma normal (3FN): los países, tipos, regiones y bandos no se repiten dentro de `guerras`.
- La relación muchos-a-muchos entre guerras y países se resuelve con `participaciones`.
- La clave foránea compuesta `(id_bando, id_guerra)` impide asociar un país a un bando de otra guerra.
- Restricciones `CHECK` para años, fechas y bajas no negativas.
- `ON DELETE CASCADE` en bandos, participaciones, batallas y tratados: al borrar una guerra se eliminan sus datos dependientes.
- `ON DELETE RESTRICT` en tipos, regiones y países: protege los catálogos.
- Vistas `vw_guerras_detalle`, `vw_bandos_participantes`, `vw_resumen_siglo` y `vw_resumen_region` para simplificar consultas.

### 3.3 Datos incluidos

34 guerras de distintas épocas, entre ellas:

- Guerras Médicas, Guerra del Peloponeso, campañas de Alejandro Magno, Guerras Púnicas y Guerra de las Galias.
- Guerra de los Cien Años, Guerras Italianas, Guerra de los Treinta Años y Guerra de Sucesión Española.
- Guerra de los Siete Años, independencia de Estados Unidos, Guerras Napoleónicas e independencias hispanoamericanas.
- Guerras del Opio, Crimea, Secesión estadounidense, Guerra del Pacífico y Guerras de los Bóeres.
- Guerra Ruso-Japonesa, Primera y Segunda Guerra Mundial, Corea, Argelia, Vietnam, Seis Días y Yom Kipur.
- Malvinas, Guerra del Golfo, Guerras Yugoslavas, Afganistán, Irak, Siria y la invasión rusa de Ucrania.

También incluye 70 países/entidades históricas, 68 bandos, 137 participaciones, 70 batallas y 31 tratados. Las cifras de bajas son estimaciones aproximadas y pueden variar según la fuente histórica.

El catálogo es una muestra representativa y ampliable: no pretende ser una lista exhaustiva de todos los conflictos de la humanidad, sino cubrir las guerras más relevantes de cada período y demostrar el funcionamiento completo de la base de datos.

> **Criterio de años:** los años a.C. se guardan como negativos (`-499` = 499 a.C.). El campo `siglo` corresponde al siglo en que **comenzó** el conflicto. MySQL no admite fechas `DATE` anteriores al año 1000, por eso las guerras antiguas usan `fecha_inicio` y `fecha_fin` nulas.

---

## 4. Instalación de Python

Se recomienda Python 3.10 o superior.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Dependencias principales: `mysql-connector-python` (acceso a MySQL) y `Flask` (interfaz web). Flask instala a su vez Jinja2, Werkzeug, Click, ItsDangerous, MarkupSafe y Blinker.

---

## 5. Configuración de la conexión

La aplicación lee variables de entorno (no hay contraseñas escritas en el código):

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DB_HOST` | `127.0.0.1` | Servidor MySQL |
| `DB_PORT` | `3306` | Puerto |
| `DB_USER` | `root` | Usuario |
| `DB_PASSWORD` | vacío | Contraseña |
| `DB_NAME` | `catalogo_guerras` | Base de datos |
| `SECRET_KEY` | clave de desarrollo | Firma de la sesión y del token CSRF de la web |

Ejemplos:

```bash
# Linux / macOS
export DB_USER=root
export DB_PASSWORD=1234
python main.py
```

```powershell
# Windows PowerShell
$env:DB_USER="root"
$env:DB_PASSWORD="1234"
python main.py
```

```bat
:: Windows CMD
set DB_USER=root
set DB_PASSWORD=1234
python main.py
```

También se pueden usar argumentos:

```bash
python main.py --host localhost --puerto 3306 --usuario root --contrasena 1234
```

> En una instalación XAMPP/WAMP típica el usuario es `root` y la contraseña está vacía. Si usa MySQL instalado por separado, use el usuario y contraseña que configuró.

---

## 6. Ejecución de la consola y funcionalidades

```bash
python main.py
```

Menú principal:

1. **Listar y filtrar guerras**: búsqueda por texto, siglo, región, tipo y rango de años.
2. **Ver ficha completa**: datos, bandos, países, batallas y tratados.
3. **Registrar nueva guerra**: validación de años, fechas, catálogos y bajas.
4. **Actualizar una guerra**: mantiene el valor actual si se deja vacío; `-` borra campos opcionales.
5. **Eliminar una guerra**: confirmación escribiendo `ELIMINAR`; borra dependencias en cascada.
6. **Reportes y consultas avanzadas**:
   - Resumen general.
   - Guerras por siglo y por región.
   - Guerras por tipo.
   - Top 10 más letales.
   - Países con más participaciones.
   - Países con más bandos victoriosos.
   - Búsqueda por bando.
   - Guerras de un país.
   - Top 3 más letales por región con `RANK() OVER` (función de ventana).
   - Guerras sin batallas registradas.
   - Guerras más largas.
7. **Ayuda** del proyecto.

Ejemplo de ejecución no interactiva:

```bash
python main.py --demo
```

---

## 7. Interfaz web estilo enciclopedia

La interfaz web está construida con **Flask** y **Jinja2** y reutiliza exactamente la misma capa de datos que la consola: `ConfiguracionBD`, `BaseDatos`, `RepositorioGuerras` y `Reportes`. No hay una segunda lógica de negocio ni datos duplicados.

### 7.1 Arranque

```bash
python run_web.py
```

Después, abre `http://127.0.0.1:5000/` en el navegador.

Opciones disponibles:

```bash
python run_web.py --puerto 8000          # cambiar el puerto
python run_web.py --host 0.0.0.0         # permitir acceso desde la red local
python run_web.py --debug                # recarga automática durante el desarrollo
```

Para la presentación final se recomienda definir una clave de sesión propia:

```bash
export SECRET_KEY="una-clave-larga-y-secreta"
python run_web.py
```

### 7.2 Páginas y rutas

| Ruta | Contenido |
|---|---|
| `/` | Portada con artículo destacado, cifras del catálogo, tipos, regiones, ranking y cronología |
| `/guerras` | Índice completo con filtros por texto, siglo, región, tipo, rango de años, conflictos en curso y orden |
| `/guerra/<id>` | Artículo con ficha de datos, contexto, bandos, países, batallas, tratados, cronología y categorías |
| `/buscar?q=...` | Búsqueda simultánea en guerras, países, bandos, batallas y tratados |
| `/guerra/nueva` | Formulario de alta con validaciones |
| `/guerra/<id>/editar` | Formulario de edición |
| `/guerra/<id>/eliminar` | Confirmación de borrado en cascada |
| `/reportes` | Todos los reportes y consultas avanzadas |
| `/pais/<id>` | Guerras y bandos de un país o entidad histórica |
| `/aleatoria` | Redirige a un artículo al azar |
| `/ayuda` | Guía de uso, instalación y solución de problemas |

### 7.3 Diseño y detalles técnicos

- **Estética enciclopédica:** cabecera con buscador, barra lateral de navegación, pestañas de artículo, ficha de datos a la derecha, tablas `wikitable`, índice de contenidos y pie de categorías.
- **Sin dependencias externas:** el CSS, el JavaScript y las ilustraciones SVG son locales, por lo que la web funciona sin conexión a Internet.
- **Adaptable:** diseño responsive para portátil, tableta y móvil; incluye estilos de impresión para los reportes.
- **Búsqueda integrada:** recorre nombres, descripciones, lugares, resultados, países, bandos, batallas y tratados.
- **Formularios protegidos:** token CSRF por sesión, validación en Python y restricciones de MySQL.
- **Errores claros:** páginas propias para 400, 404, 409, 500 y 503, con ayuda específica cuando no hay conexión con la base de datos.
- **Accesibilidad:** enlace para saltar al contenido, etiquetas asociadas a los campos, foco visible, textos alternativos y contraste cuidado.
- **Atajos:** la tecla `/` lleva al buscador y el botón «Imprimir» de los reportes lanza la impresión del navegador.

---

## 8. Consultas avanzadas en SQL

El archivo `sql/consultas_avanzadas.sql` contiene 15 consultas listas para pegar en phpMyAdmin:

- Resumen general con subconsultas.
- Filtros por siglo, región y bando.
- Rankings de letalidad y de países con más victorias.
- Agregaciones con `GROUP BY`, `COUNT`, `SUM` y `AVG`.
- CTE (`WITH`) y funciones de ventana (`RANK() OVER`, `SUM() OVER`).
- `LEFT JOIN ... IS NULL` para detectar guerras sin batallas.
- Duración de los conflictos y guerras aún abiertas.

La misma lógica está implementada en `app/reportes.py` para ejecutarse desde el menú de Python.

---

## 9. Decisiones técnicas

- **Consultas parametrizadas** (`%s`) en todas las operaciones: evita inyección SQL.
- **Transacciones**: cada operación hace `COMMIT`; ante cualquier error se ejecuta `ROLLBACK`.
- **Cierre garantizado** de cursores y conexiones mediante `contextmanager`.
- **Validación en dos capas**: Python comprueba tipos, rangos y fechas; MySQL aplica `CHECK`, `UNIQUE` y claves foráneas.
- **Errores traducidos** a mensajes claros (duplicados, claves foráneas, credenciales, base inexistente).
- **Separación por capas**: configuración, acceso a datos, repositorio, reportes e interfaz.
- **Sin ORM**: se usa SQL explícito para demostrar el dominio de MySQL, tal como pide el proyecto.

---

## 10. Solución de problemas

**`ModuleNotFoundError: No module named 'mysql'`**

```bash
python -m pip install -r requirements.txt
```

**`Access denied for user 'root'@'localhost'`**

Revise `DB_USER` y `DB_PASSWORD`. En XAMPP la contraseña suele estar vacía.

**`Unknown database 'catalogo_guerras'`**

Importe `sql/catalogo_guerras.sql` en phpMyAdmin.

**`Can't connect to MySQL server`**

Inicie MySQL desde el panel de XAMPP/WAMP/Laragon o el servicio del sistema. Compruebe `DB_HOST` y `DB_PORT`.

**Error de autenticación `auth_socket` en Linux**

Cree un usuario específico para la aplicación:

```sql
CREATE USER 'catalogo'@'localhost' IDENTIFIED BY 'catalogo123';
GRANT ALL PRIVILEGES ON catalogo_guerras.* TO 'catalogo'@'localhost';
FLUSH PRIVILEGES;
```

Luego:

```bash
export DB_USER=catalogo
export DB_PASSWORD=catalogo123
python main.py
```

**Acentos o caracteres extraños**

La base usa `utf8mb4`. Importe el archivo como UTF-8 y mantenga `charset=utf8mb4` en la conexión.

**Las consultas de los reportes fallan**

Se requieren MySQL 8.0+ o MariaDB 10.5+ por el uso de CTE y funciones de ventana. Actualice el servidor o ejecute las consultas equivalentes sin CTE del resto del archivo.

---

## 11. Cómo ampliar el catálogo

Desde la propia aplicación:

```text
Menú → 3. Registrar nueva guerra
```

Desde phpMyAdmin, por ejemplo:

```sql
INSERT INTO guerras
(nombre, anio_inicio, anio_fin, siglo, id_tipo, id_region, lugar, resultado, bajas_totales, descripcion)
VALUES
('Guerra de los Treinta Años', 1618, 1648, 'XVII', 3, 1,
 'Europa central', 'Paz de Westfalia', 8000000, 'Descripción...');
```

Después se pueden agregar bandos, participaciones, batallas y tratados con sus respectivas claves foráneas. El repositorio se puede ampliar con métodos CRUD para esas tablas si el proyecto lo requiere.

---

## 12. Comprobación académica

- [x] Base de datos creada con `CREATE DATABASE`.
- [x] Tablas con `PRIMARY KEY`, `FOREIGN KEY`, `UNIQUE`, `CHECK` e índices.
- [x] Relación muchos-a-muchos mediante tabla intermedia.
- [x] Datos reales de conflictos de la Antigüedad, Edad Media, Edad Moderna y Contemporánea.
- [x] CRUD completo en Python.
- [x] Consultas con `JOIN`, `GROUP BY`, subconsultas, CTE y funciones de ventana.
- [x] Interfaz de consola con validaciones y confirmaciones.
- [x] Interfaz web estilo enciclopedia con CRUD, búsqueda y reportes.
- [x] Protección CSRF y manejo personalizado de errores en la web.
- [x] Diseño responsive y recursos locales, sin CDNs.
- [x] Documentación de instalación, configuración y ejecución.

---

## 13. Pruebas realizadas

- Script SQL importado correctamente en MariaDB 10.11 (compatible con MySQL 8.0+).
- Verificación de 34 guerras, 68 bandos, 137 participaciones, 70 batallas y 31 tratados.
- Las 15 consultas de `sql/consultas_avanzadas.sql` se ejecutaron sin errores.
- CRUD probado contra el servidor: creación, lectura, actualización, borrado, duplicados y filtros.
- Reportes probados desde `python main.py --demo`.
- Interfaz web probada con el cliente de pruebas de Flask: portada, búsqueda, índice, filtros, artículo, país, reportes, ayuda, 404 y artículo aleatorio.
- CRUD web completo probado: alta, lectura, edición, borrado, formulario inválido y petición sin token CSRF.
- Capturas de la interfaz revisadas en Chrome en escritorio (1440 px) y móvil (390 px).
- Verificado con Python 3.12, `mysql-connector-python` 26.10.0 y Flask 3.1.3.
# Guerras
