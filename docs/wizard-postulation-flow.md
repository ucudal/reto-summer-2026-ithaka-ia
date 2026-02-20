# Flujo del Wizard de Postulación — Ithaka

Este documento describe el flujo completo de preguntas que el chatbot realiza al usuario durante el proceso de postulación a Ithaka. Está pensado para que el equipo de producto entienda la experiencia del postulante de punta a punta.

---

## Visión general

El wizard se divide en dos grandes bloques:

| Bloque | Preguntas | Descripción | ¿Obligatorio? |
|---|---|---|---|
| **Datos personales** | 1 – 11 | Información de contacto e identificación | Sí |
| **Comentarios (sin idea)** | 12 | Comentarios adicionales para quienes no tienen idea | No (opcional) |
| **Datos del emprendimiento** | 13 – 20 | Preguntas evaluativas sobre el proyecto | Sí (solo si respondió "SI" en la pregunta 11) |

> **Punto de bifurcación:** La pregunta 11 determina si el flujo continúa hacia las preguntas del emprendimiento o finaliza con un comentario libre.

---

## Flujo paso a paso

### Bloque 1 — Datos Personales (Preguntas 1 a 11)

---

#### Pregunta 1 — Nombre completo
> Comencemos el proceso de postulación de Ithaka 🚀
>
> Comencemos con tus datos personales.
>
> **Apellido, Nombre**
>
> Por favor, ingresa tu apellido y nombre completo:

- **Tipo:** Texto libre
- **Obligatoria:** Sí

---

#### Pregunta 2 — Correo electrónico
> **Correo electrónico**
>
> Ingresa tu dirección de correo electrónico:

- **Tipo:** Email
- **Obligatoria:** Sí
- **Nota interna:** Este email se usa para persistir la sesión y permitir que el usuario continúe más tarde.

---

#### Pregunta 3 — Teléfono
> **Celular o Teléfono**
>
> Ingresa tu número de teléfono (incluye código de país si es necesario):

- **Tipo:** Número de teléfono
- **Obligatoria:** Sí

---

#### Pregunta 4 — Documento de identidad
> **Número de Documento de Identidad**
>
> Ingresa tu número de cédula o documento de identidad:

- **Tipo:** Texto (cédula / CI)
- **Obligatoria:** Sí

---

#### Pregunta 5 — País y localidad de residencia
> **País y localidad de residencia**
>
> Indica tu país y ciudad de residencia:

- **Tipo:** Texto libre
- **Obligatoria:** Sí

---

#### Pregunta 6 — Campus UCU preferido
> **Campus UCU**
>
> ¿En qué Campus de la UCU preferís contactarte con Ithaka?
>
> Opciones:
> - Maldonado
> - Montevideo
> - Salto

- **Tipo:** Opción única
- **Obligatoria:** Sí
- **Opciones:** Maldonado · Montevideo · Salto

---

#### Pregunta 7 — Relación con la UCU
> **Relación con la UCU**
>
> ¿Cuál es tu relación con la UCU?
>
> Opciones:
> - Estudiante
> - Graduado
> - Funcionario o Docente
> - Solía estudiar allí
> - No tengo relación con la UCU

- **Tipo:** Opción única
- **Obligatoria:** Sí
- **Nota interna:** La respuesta a esta pregunta condiciona la aparición de la pregunta 8.

---

#### Pregunta 8 — Facultad UCU *(condicional)*
> **Facultad UCU**
>
> En caso de tener relación con la UCU, ¿en qué facultad estudiaste/trabajas?
>
> Opciones:
> - Ciencias de la Salud
> - Ciencias Empresariales
> - Ciencias Humanas + Derecho
> - Ingeniería y Tecnologías

- **Tipo:** Opción única
- **Obligatoria:** No
- **Se muestra solo si** la respuesta a la pregunta 7 fue: Estudiante, Graduado, Funcionario o Docente, o Solía estudiar allí.
- **No se muestra si** el usuario seleccionó "No tengo relación con la UCU".

---

#### Pregunta 9 — ¿Cómo llegaste a Ithaka?
> **¿Cómo llegaste a Ithaka?**
>
> Opciones:
> - Redes Sociales
> - Curso de Grado
> - Curso de Posgrado
> - Buscando en la web
> - Por alguna actividad de UCU
> - A través de ANII/ANDE cuando buscaba una IPE

- **Tipo:** Opción única
- **Obligatoria:** Sí

---

#### Pregunta 10 — Motivación
> **Motivación**
>
> ¿Qué te motiva para escribirnos?
>
> Cuéntanos qué te impulsa a contactar con Ithaka:

- **Tipo:** Texto libre (mínimo ~10 caracteres)
- **Obligatoria:** Sí

---

#### Pregunta 11 — ¿Tiene idea o emprendimiento? *(punto de bifurcación)*
> **¿Tienes una idea o emprendimiento?**
>
> Opciones:
> - NO
> - SI
>
> *Si tu respuesta es SI, continuarás completando el formulario completo.*

- **Tipo:** Sí / No
- **Obligatoria:** Sí

> **Bifurcación del flujo:**
> - Responde **NO** → se pasa a la pregunta 12 (comentarios opcionales) y el formulario finaliza.
> - Responde **SI** → se omite la pregunta 12 y se continúa con el bloque del emprendimiento (preguntas 13 a 20).

---

### Bloque 2A — Cierre sin emprendimiento (Pregunta 12)

*Solo se muestra si la pregunta 11 fue respondida con "NO".*

---

#### Pregunta 12 — Comentarios adicionales
> **Comentarios adicionales**
>
> Desde ya muchas gracias por compartirnos tus datos de contacto. Puedes dejarnos comentarios adicionales aquí:
>
> *(Opcional)*

- **Tipo:** Texto libre
- **Obligatoria:** No

---

### Bloque 2B — Datos del emprendimiento (Preguntas 13 a 20)

*Solo se muestran si la pregunta 11 fue respondida con "SI".*

---

#### Pregunta 13 — Composición del equipo
> **Composición del equipo**
>
> Si tienes equipo de trabajo, ¿cómo está compuesto el equipo?
>
> Incluye:
> - Datos de los otros integrantes (Nombres y Apellidos, Celular y Correo electrónico)
> - ¿Qué actividades/roles desempeña cada uno?
> - Experiencias previas, ¿Es el primer emprendimiento?

- **Tipo:** Texto libre evaluativo
- **Obligatoria:** Sí

---

#### Pregunta 14 — Problema que resuelve
> **Problema que resuelve**
>
> ¿Qué problema resuelve el emprendimiento? O ¿qué oportunidad/necesidad has detectado?
>
> Describe claramente el problema o necesidad que has identificado:

- **Tipo:** Texto libre evaluativo
- **Obligatoria:** Sí

---

#### Pregunta 15 — La solución
> **La solución**
>
> ¿Cuál es la solución? ¿Quiénes son los clientes?
>
> Describe tu solución y define claramente tu mercado objetivo:

- **Tipo:** Texto libre evaluativo
- **Obligatoria:** Sí

---

#### Pregunta 16 — Innovación y valor diferencial
> **Innovación y valor diferencial**
>
> ¿Por qué es innovador o tiene valor diferencial?
>
> Explícanos también:
> - ¿Cómo se resuelve este problema hoy?
> - ¿Por qué te van a comprar a ti en vez de a otros?

- **Tipo:** Texto libre evaluativo
- **Obligatoria:** Sí

---

#### Pregunta 17 — Modelo de negocio
> **Modelo de negocio**
>
> ¿Cómo hace dinero este proyecto?
>
> Describe tu modelo de negocio y fuentes de ingresos:

- **Tipo:** Texto libre evaluativo
- **Obligatoria:** Sí

---

#### Pregunta 18 — Etapa del proyecto
> **Etapa del proyecto**
>
> ¿En qué etapa está el proyecto?
>
> Opciones:
> - Idea inicial
> - Prototipo/MVP
> - Producto desarrollado
> - Ventas/Tracción inicial
> - Escalando

- **Tipo:** Opción única
- **Obligatoria:** Sí
- **Opciones:** Idea inicial · Prototipo/MVP · Producto desarrollado · Ventas/Tracción inicial · Escalando

---

#### Pregunta 19 — Apoyo necesario de Ithaka
> **Apoyo necesario**
>
> ¿Cuál/es de estos apoyos necesitas de Ithaka?
>
> Opciones:
> - Tutoría para validar la idea
> - Soporte para armar el plan de negocios
> - Ayuda para obtener financiamiento para el proyecto
> - Capacitación
> - Ayuda para un tema específico
> - Otro

- **Tipo:** Opción única (o múltiple)
- **Obligatoria:** Sí

---

#### Pregunta 20 — Información adicional
> **Información adicional**
>
> ¿Algo más que quieras contarnos?
>
> *(Opcional - Cualquier información adicional que consideres relevante)*

- **Tipo:** Texto libre
- **Obligatoria:** No

---

### Mensaje de cierre

Una vez completado el formulario, el bot muestra:

> ¡Muchas gracias por completar el formulario de postulación de Ithaka! 🎉
>
> Hemos registrado todas tus respuestas. Nuestro equipo revisará tu postulación y te contactaremos a la brevedad.
>
> ¡Esperamos poder acompañarte en tu emprendimiento!

---

## Diagrama de flujo resumido

```
Inicio del wizard
      │
      ▼
Preguntas 1 a 7 (datos personales, todas obligatorias)
      │
      ▼
¿Tiene relación con la UCU? (pregunta 7)
  ├── Sí ──► Pregunta 8 (Facultad UCU)
  └── No ──► (se omite pregunta 8)
      │
      ▼
Preguntas 9, 10 (canal de llegada y motivación)
      │
      ▼
Pregunta 11: ¿Tiene idea o emprendimiento?
  ├── NO ──► Pregunta 12 (comentarios opcionales) ──► FIN
  └── SI ──► Preguntas 13 a 20 (bloque del emprendimiento) ──► FIN
```

---

## Resumen de campos capturados

| # | Campo | Tipo de respuesta | Obligatorio |
|---|---|---|---|
| 1 | Apellido y Nombre | Texto libre | Sí |
| 2 | Correo electrónico | Email | Sí |
| 3 | Teléfono | Número | Sí |
| 4 | Documento de identidad | Texto | Sí |
| 5 | País y localidad | Texto libre | Sí |
| 6 | Campus UCU preferido | Opción única | Sí |
| 7 | Relación con la UCU | Opción única | Sí |
| 8 | Facultad UCU | Opción única | No (condicional) |
| 9 | Canal de llegada a Ithaka | Opción única | Sí |
| 10 | Motivación | Texto libre | Sí |
| 11 | ¿Tiene idea/emprendimiento? | Sí / No | Sí |
| 12 | Comentarios adicionales (sin idea) | Texto libre | No |
| 13 | Composición del equipo | Texto libre | Sí* |
| 14 | Problema que resuelve | Texto libre | Sí* |
| 15 | Solución y clientes | Texto libre | Sí* |
| 16 | Innovación y valor diferencial | Texto libre | Sí* |
| 17 | Modelo de negocio | Texto libre | Sí* |
| 18 | Etapa del proyecto | Opción única | Sí* |
| 19 | Apoyo necesario de Ithaka | Opción única | Sí* |
| 20 | Información adicional (con idea) | Texto libre | No* |

*\* Solo aplica cuando el usuario respondió "SI" en la pregunta 11.*
