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
Esto puede hacerse por script (carga inicial) o por endpoint (carga desde frontend/admin).

## 5. Endpoints recomendados para gestion de documentos

A nivel producto/API, lo ideal es exponer:
- POST /api/v1/documents: alta de documento (crea embedding y guarda).
- GET /api/v1/documents: listado de documentos cargados (con filtros opcionales).
- DELETE /api/v1/documents/{id}: eliminacion de un documento especifico.
Con esto tenes un CRUD minimo para administrar la base de conocimiento.

## 6. Flujo operativo recomendado

1) Cargar documentos base para arrancar.
2) Validar que las respuestas FAQ sean coherentes.
3) Publicar endpoints de administracion (POST/GET/DELETE).
4) Definir control de acceso (solo admins pueden subir/eliminar).
5) Agregar trazabilidad (quien subio o elimino cada documento).

## 7. Resumen ejecutivo

El sistema ya tiene la estructura para conversar, enrutar y persistir. Lo que faltaba para tu objetivo era formalizar la gestion de documentos como API de administracion (alta, listado, baja). Una vez expuestos esos endpoints, el mantenimiento del conocimiento FAQ se vuelve simple y operativo para negocio.
