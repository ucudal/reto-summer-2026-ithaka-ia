"""
Preguntas del wizard de postulación de Ithaka
"""

# Preguntas del wizard organizadas por categorías
WIZARD_QUESTIONS = {
    # Preguntas 1-11: Datos Personales (Obligatorias)
    1: {
        "text": "Comencemos el proceso de postulación de Ithaka 🚀\n\nComencemos con tus datos personales.\n\n**Apellido, Nombre**\n\nPor favor, ingresa tu apellido y nombre completo:",
        "type": "personal",
        "required": True,
        "validation": "name",
        "field_name": "full_name"
    },
    2: {
        "text": "**Correo electrónico**\n\nIngresa tu dirección de correo electrónico:",
        "type": "personal",
        "required": True,
        "validation": "email",
        "field_name": "email",
        "note": "Con este email persistiremos tu sesión y podrás continuar más tarde si es necesario."
    },
    3: {
        "text": "**Celular o Teléfono**\n\nIngresa tu número de teléfono (incluye código de país si es necesario):",
        "type": "personal",
        "required": True,
        "validation": "phone",
        "field_name": "phone"
    },
    4: {
        "text": "**Número de Documento de Identidad**\n\nIngresa tu número de cédula o documento de identidad:",
        "type": "personal",
        "required": True,
        "validation": "ci",
        "field_name": "document_id"
    },
    5: {
        "text": "**País y localidad de residencia**\n\nIndica tu país y ciudad de residencia:",
        "type": "personal",
        "required": True,
        "validation": "location",
        "field_name": "location"
    },
    6: {
        "text": "**Campus UCU**\n\n¿En qué Campus de la UCU preferís contactarte con Ithaka?\n\nOpciones:\n• Maldonado\n• Montevideo  \n• Salto",
        "type": "personal",
        "required": True,
        "validation": "campus",
        "options": ["Maldonado", "Montevideo", "Salto"],
        "field_name": "preferred_campus"
    },
    7: {
        "text": "**Relación con la UCU**\n\n¿Cuál es tu relación con la UCU?\n\nOpciones:\n• Estudiante\n• Graduado\n• Funcionario o Docente\n• Solía estudiar allí\n• No tengo relación con la UCU",
        "type": "personal",
        "required": True,
        "validation": "ucu_relation",
        "options": ["Estudiante", "Graduado", "Funcionario o Docente", "Solía estudiar allí", "No tengo relación con la UCU"],
        "field_name": "ucu_relation"
    },
    8: {
        "text": "**Facultad UCU**\n\nEn caso de tener relación con la UCU, ¿en qué facultad estudiaste/trabajas?\n\nOpciones:\n• Ciencias de la Salud\n• Ciencias Empresariales\n• Ciencias Humanas + Derecho\n• Ingeniería y Tecnologías",
        "type": "personal",
        "required": False,
        "conditional": True,
        "condition_field": "ucu_relation",
        "condition_values": ["Estudiante", "Graduado", "Funcionario o Docente", "Solía estudiar allí"],
        "validation": "faculty",
        "options": ["Ciencias de la Salud", "Ciencias Empresariales", "Ciencias Humanas + Derecho", "Ingeniería y Tecnologías"],
        "field_name": "faculty"
    },
    9: {
        "text": "**¿Cómo llegaste a Ithaka?**\n\nOpciones:\n• Redes Sociales\n• Curso de Grado\n• Curso de Posgrado\n• Buscando en la web\n• Por alguna actividad de UCU\n• A través de ANII/ANDE cuando buscaba una IPE",
        "type": "personal",
        "required": True,
        "validation": "discovery_method",
        "options": ["Redes Sociales", "Curso de Grado", "Curso de Posgrado", "Buscando en la web", "Por alguna actividad de UCU", "A través de ANII/ANDE cuando buscaba una IPE"],
        "field_name": "discovery_method"
    },
    10: {
        "text": "**Motivación**\n\n¿Qué te motiva para escribirnos?\n\nCuéntanos qué te impulsa a contactar con Ithaka:",
        "type": "personal",
        "required": True,
        "validation": "text_min_length",
        "min_length": 10,
        "field_name": "motivation"
    },
    11: {
        "text": "**¿Tienes una idea o emprendimiento?**\n\nOpciones:\n• NO\n• SI\n\n*Si tu respuesta es SI, continuarás completando el formulario completo.*",
        "type": "personal",
        "required": True,
        "validation": "yes_no",
        "options": ["NO", "SI"],
        "field_name": "has_idea",
        "note": "Si respondes NO, completaremos tu registro básico. Si respondes SI, continuaremos con preguntas sobre tu emprendimiento."
    },
    12: {
        "text": "**Comentarios adicionales**\n\nDesde ya muchas gracias por compartirnos tus datos de contacto. Puedes dejarnos comentarios adicionales aquí:\n\n*(Opcional)*",
        "type": "optional",
        "required": False,
        "validation": "optional_text",
        "field_name": "additional_comments"
    },

    # Preguntas 13-20: Sobre el emprendimiento (Evaluativas)
    13: {
        "text": "**Composición del equipo**\n\nSi tienes equipo de trabajo, ¿cómo está compuesto el equipo?\n\nIncluye:\n• Datos de los otros integrantes (Nombres y Apellidos, Celular y Correo electrónico)\n• ¿Qué actividades/roles desempeña cada uno?\n• Experiencias previas, ¿Es el primer emprendimiento?",
        "type": "evaluative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "rubrica",
        "rubrica_key": "pregunta_13",
        "field_name": "team_composition"
    },
    14: {
        "text": "**Problema que resuelve**\n\n¿Qué problema resuelve el emprendimiento? O ¿qué oportunidad/necesidad has detectado?\n\nDescribe claramente el problema o necesidad que has identificado:",
        "type": "evaluative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "rubrica",
        "rubrica_key": "pregunta_14",
        "field_name": "problem_description"
    },
    15: {
        "text": "**La solución**\n\n¿Cuál es la solución? ¿Quiénes son los clientes?\n\nDescribe tu solución y define claramente tu mercado objetivo:",
        "type": "evaluative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "rubrica",
        "rubrica_key": "pregunta_15",
        "field_name": "solution_description"
    },
    16: {
        "text": "**Innovación y valor diferencial**\n\n¿Por qué es innovador o tiene valor diferencial?\n\nExplícanos también:\n• ¿Cómo se resuelve este problema hoy?\n• ¿Por qué te van a comprar a ti en vez de a otros?",
        "type": "evaluative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "rubrica",
        "rubrica_key": "pregunta_16",
        "field_name": "innovation_differential"
    },
    17: {
        "text": "**Modelo de negocio**\n\n¿Cómo hace dinero este proyecto?\n\nDescribe tu modelo de negocio y fuentes de ingresos:",
        "type": "evaluative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "rubrica",
        "rubrica_key": "pregunta_17",
        "field_name": "business_model"
    },
    18: {
        "text": "**Etapa del proyecto**\n\n¿En qué etapa está el proyecto?\n\nOpciones:\n• Idea inicial\n• Prototipo/MVP\n• Producto desarrollado\n• Ventas/Tracción inicial\n• Escalando",
        "type": "informative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "project_stage",
        "options": ["Idea inicial", "Prototipo/MVP", "Producto desarrollado", "Ventas/Tracción inicial", "Escalando"],
        "rubrica_key": "pregunta_18",
        "field_name": "project_stage"
    },
    19: {
        "text": "**Apoyo necesario**\n\n¿Cuál/es de estos apoyos necesitas de Ithaka?\n\nOpciones:\n• Tutoría para validar la idea\n• Soporte para armar el plan de negocios\n• Ayuda para obtener financiamiento para el proyecto\n• Capacitación\n• Ayuda para un tema específico\n• Otro",
        "type": "informative",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": True,
        "validation": "support_needed",
        "options": ["Tutoría para validar la idea", "Soporte para armar el plan de negocios", "Ayuda para obtener financiamiento para el proyecto", "Capacitación", "Ayuda para un tema específico", "Otro"],
        "rubrica_key": "pregunta_19",
        "field_name": "support_needed"
    },
    20: {
        "text": "**Información adicional**\n\n¿Algo más que quieras contarnos?\n\n*(Opcional - Cualquier información adicional que consideres relevante)*",
        "type": "optional",
        "conditional": True,
        "condition_field": "has_idea",
        "condition_values": ["SI"],
        "required": False,
        "validation": "optional_text",
        "rubrica_key": "pregunta_20",
        "field_name": "additional_info"
    }
}



