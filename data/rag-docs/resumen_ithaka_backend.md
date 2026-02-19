# Ithaka Backend - Guia Simple

## 1. Como funciona el sistema (vision general)

- El backend recibe mensajes del usuario (desde web o websocket), decide quien responde y devuelve una respuesta al frontend.
- Internamente usa una orquestacion de agentes: un supervisor analiza la intencion y deriva la consulta al agente correcto (FAQ o Wizard).
- El agente FAQ responde preguntas frecuentes usando busqueda semantica sobre una base de conocimiento con embeddings.
- El agente Wizard guia al usuario en un flujo conversacional de postulacion y guarda su estado paso a paso.

## 2. Que hace la sincronizacion con backend

Cada vez que llega un mensaje:
- Se crea o recupera la conversacion del usuario.
- Se ejecuta el workflow de agentes para decidir y generar la respuesta.
- Se persiste historial de mensajes y estado relevante (por ejemplo, avance del wizard).
Resultado: frontend y backend quedan sincronizados porque la fuente de verdad queda guardada en base de datos.

## 3. Donde viven los documentos/FAQ

- La informacion de preguntas y respuestas se guarda como registros en una tabla de embeddings (faq_embeddings).
- Cada registro suele tener: pregunta, respuesta, embedding vectorial y fecha de creacion.
Cuando el usuario pregunta algo, el sistema busca los registros mas parecidos semanticamente y responde en base a ellos.

## 4. Como subir documentos nuevos

Conceptualmente, subir un documento nuevo implica:
1) Recibir el contenido (pregunta/respuesta o texto fuente).
2) Convertir ese contenido a embedding.
3) Guardarlo en base de datos.
4) Dejarlo disponible para futuras busquedas FAQ.
Hoy puede hacerse por endpoint (carga desde frontend/admin) y tambien por scripts de carga inicial.

## 5. Endpoints implementados para gestion de documentos

Actualmente estan disponibles:
- POST /api/v1/documents: alta manual de documento (question + answer).
- POST /api/v1/documents/upload: subida de archivo (pdf/txt/md/csv), extraccion de texto, chunking y embeddings por fragmento.
- GET /api/v1/documents: listado de documentos cargados con paginacion (`limit`, `offset`).
- DELETE /api/v1/documents/{id}: eliminacion de un documento especifico.
Con esto tenes gestion operativa de base de conocimiento y pipeline de ingesta para RAG.

## 6. Flujo operativo recomendado

1) Cargar documentos base para arrancar.
2) Validar que las respuestas FAQ sean coherentes.
3) Publicar y validar endpoints de administracion y upload (POST/GET/DELETE + upload).
4) Definir control de acceso (solo admins pueden subir/eliminar).
5) Agregar trazabilidad (quien subio o elimino cada documento).

## 7. Resumen ejecutivo

El sistema ya tiene la estructura para conversar, enrutar y persistir, y ya incorpora endpoints para gestion de documentos y carga de archivos para RAG. El mantenimiento del conocimiento FAQ queda operativo para negocio y extensible para nuevos formatos.

## 8. Actualizacion tecnica reciente

Se desacoplo el modulo Documents en capas:
- Router/API: `app/api/v1/documents.py`
- Schemas: `app/api/v1/schemas/documents.py`
- Ingesta de archivos: `app/services/document_ingestion_service.py`

Esto mejora mantenibilidad y facilita que otros equipos extiendan formatos o contratos sin mezclar logica de parsing en el router.
