# Ithaka IA - Guia de Endpoints: Documents

Version: 1.0

## 1. Alcance

Este documento describe los endpoints del modulo **Documents** del backend de Ithaka IA.
Estos endpoints permiten gestionar contenido de conocimiento para el sistema **RAG**, persistido en la tabla `faq_embeddings`.

## 2. Informacion general

- Base path: `/api/v1`
- Tag en Swagger: `Documents`
- Tabla de persistencia: `faq_embeddings`
- Formatos de archivo soportados: `pdf`, `txt`, `md`, `csv`

## 3. Modelos de datos

### 3.1 DocumentCreate

Request de `POST /documents`.

| Campo | Tipo | Requerido | Restricciones |
| `question` | string | Si | Minimo 3 caracteres |
| `answer` | string | Si | Minimo 3 caracteres |

### 3.2 DocumentResponse

Response de `GET /documents` y `POST /documents`.

| Campo | Tipo |
|---|---|
| `id` | integer |
| `question` | string |
| `answer` | string |
| `created_at` | datetime \| null |

### 3.3 DocumentUploadResponse

Response de `POST /documents/upload`.

| Campo | Tipo |
|---|---|
| `filename` | string |
| `file_type` | string |
| `chunks_created` | integer |
| `document_ids` | integer[] |

## 4. Endpoint: Crear documento

- Metodo: `POST`
- Ruta: `/api/v1/documents`
- Content-Type: `application/json`

### Objetivo

Crear un documento manual y generar su embedding a partir de `question + answer`.

### Ejemplo de request

```json
{
  "question": "Que es Ithaka?",
  "answer": "Ithaka es el centro de emprendimiento de UCU."
}
```

### Respuesta exitosa

- `201 Created`
- Retorna `DocumentResponse`

### Errores posibles

- `422`: error de validacion (campos faltantes o longitud insuficiente)
- `500`: error al generar embeddings o al persistir en base de datos

## 5. Endpoint: Subida de archivo (Chunk + Embedding)

- Metodo: `POST`
- Ruta: `/api/v1/documents/upload`
- Content-Type: `multipart/form-data`

### Objetivo

Subir un archivo, extraer su texto, dividirlo en fragmentos (chunks), generar embeddings por chunk y persistir cada chunk como una fila independiente.

### Campo requerido (form-data)

- `file`: archivo binario

### Parametros de query

| Parametro | Tipo | Default | Minimo | Maximo |
|---|---|---|---|---|
| `chunk_size` | integer | 1200 | 200 | 4000 |
| `chunk_overlap` | integer | 150 | 0 | 1000 |

### Reglas de validacion

- El archivo debe tener nombre.
- El archivo no puede estar vacio.
- Tamano maximo permitido: `20 MB`.
- `chunk_overlap` debe ser menor que `chunk_size`.
- Extensiones permitidas: `pdf`, `txt`, `md`, `csv`.
- El archivo debe contener texto procesable.

### Comportamiento por formato

- `txt` / `md`: decodificacion UTF-8, con fallback a Latin-1.
- `csv`: parseo por filas y transformacion a texto plano (`columna: valor`).
- `pdf`: extraccion de texto usando `pypdf`.

### Comportamiento de persistencia

- Cada chunk se guarda como una fila en `FAQEmbedding`.
- `question` se genera como: `<filename> - fragmento <i>/<n>`.
- `answer` contiene el texto del chunk.
- La operacion es transaccional; ante cualquier error se ejecuta rollback completo.

### Respuesta exitosa

- `201 Created`
- Retorna `DocumentUploadResponse`

### Errores posibles

- `400`: parametros invalidos, formato no soportado o archivo sin texto util
- `500`: error al generar embeddings o al persistir en base de datos

## 6. Endpoint: Listar documentos

- Metodo: `GET`
- Ruta: `/api/v1/documents`

### Objetivo

Listar documentos persistidos, ordenados por fecha de creacion descendente.

### Parametros de query

| Parametro | Tipo | Default | Minimo | Maximo |
|---|---|---|---|---|
| `limit` | integer | 50 | 1 | 200 |
| `offset` | integer | 0 | 0 | - |

### Respuesta exitosa

- `200 OK`
- Retorna `DocumentResponse[]`

### Errores posibles

- `500`: error de lectura en base de datos

## 7. Endpoint: Eliminar documento

- Metodo: `DELETE`
- Ruta: `/api/v1/documents/{document_id}`

### Objetivo

Eliminar un documento especifico por ID.

### Parametro de path

| Parametro | Tipo |
|---|---|
| `document_id` | integer |

### Respuesta exitosa

- `200 OK`

```json
{
  "message": "Documento <id> eliminado correctamente"
}
```

### Errores posibles

- `404`: documento no encontrado
- `500`: error de base de datos al eliminar

## 8. Flujo end-to-end recomendado

1. Subir archivo con `POST /documents/upload`.
2. Obtener IDs generados desde `document_ids`.
3. Verificar persistencia con `GET /documents`.
4. Eliminar chunks especificos con `DELETE /documents/{id}` cuando corresponda.

## 9. Notas operativas

- Debe existir el esquema de base de datos y la tabla `faq_embeddings`.
- `POST /documents/upload` requiere conectividad con OpenAI para generar embeddings.
- Dependencias runtime necesarias:
  - `python-multipart`
  - `pypdf`
- Recomendado: proteger `create`, `upload` y `delete` con autenticacion y control de roles.
