#!/usr/bin/env python3
"""
Script para poblar la base de datos con FAQs de Ithaka
Uso: python scripts/populate_faqs.py
"""

import asyncio
import sys
from pathlib import Path

from app.db.config.database import get_async_session
from app.services.embedding_service import embedding_service

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def populate_faqs():
    """Pobla la base de datos con FAQs de Ithaka"""

    print("📚 Poblando base de datos con FAQs de Ithaka...")
    print("=" * 50)

    # FAQs data
    FAQS_DATA = [
        # Cursos y capacitaciones
        {
            "question": "¿Qué cursos electivos puedo hacer en Ithaka?",
            "answer": "Tenemos un PDF con todos los cursos electivos https://bit.ly/ElectivasIthaka. Si te interesa el paquete completo de cursos puedes dirigirte al minor de innovación y emprendimiento https://minor-innovacion-emprend-6ucsomp.gamma.site/"
        },
        {
            "question": "cursos de emprendimiento capacitaciones ithaka formacion",
            "answer": "En Ithaka ofrecemos múltiples cursos y capacitaciones en emprendimiento e innovación. Tenemos cursos electivos para estudiantes UCU, el minor de innovación y emprendimiento, y capacitaciones abiertas para la comunidad. Todos nuestros cursos son gratuitos para la comunidad UCU. Más información: https://bit.ly/ElectivasIthaka"
        },

        # Programa Fellows - múltiples variaciones
        {
            "question": "¿Qué es el programa Fellows?",
            "answer": "Es un programa online creado por la universidad de Stanford y dictado por la universidad de Twente que te ayuda a desarrollar habilidades intraemprendedoras en tu experiencia universitaria. Es un programa que desde UCU-Ithaka seleccionamos y becamos 4 estudiantes para que se conviertan en agentes de cambio. Además los seleccionados tienen la posibilidad de asistir al evento internacional de meetup de fellows un viaje en la universidad de Twente, Países Bajos durante 3 días (los pasajes son costeados por la UCU). https://programa-university-inno-k2jjjij.gamma.site/"
        },
        {
            "question": "programa fellows como funciona que es becas stanford twente",
            "answer": "El programa Fellows es una beca completa que te ayuda a desarrollar habilidades de intraemprendimiento. Seleccionamos solo 4 estudiantes UCU por año. Incluye formación online con Stanford/Twente y viaje a Países Bajos. Es completamente gratuito y una oportunidad única de crecimiento personal y profesional. https://programa-university-inno-k2jjjij.gamma.site/"
        },
        {
            "question": "¿Cuándo es la convocatoria para el programa Fellows?",
            "answer": "Durante marzo-abril se lanza la convocatoria para postulantes al programa, y luego de un proceso de selección de aprox. 1 mes con entrevistas grupales e individuales, se seleccionan 4 participantes."
        },

        # Freelancer y emprendimiento profesional
        {
            "question": "¿Quiero emprender como freelancer, cómo hago?",
            "answer": "Desarrolla una marca personal y trabajar desde tu profesión es posible pero es necesario saber y haber desarrollando ciertos conocimientos, habilidades y competencias. En Ithaka tenemos cursos específicos si te interesa emprender desde tu profesión."
        },
        {
            "question": "freelance independiente marca personal profesion emprender trabajo",
            "answer": "Para emprender como freelancer necesitas desarrollar tu marca personal y habilidades específicas. En Ithaka te ayudamos con cursos sobre emprendimiento profesional, desarrollo de marca personal, y herramientas para el trabajo independiente. Nuestros mentores tienen experiencia en diferentes industrias."
        },

        # Información general de Ithaka
        {
            "question": "¿El Centro Ithaka es exclusivo para estudiantes y egresados UCU?",
            "answer": "No, el Centro Ithaka forma parte del ecosistema emprendedor y atiende a la comunidad universitaria UCU en general (futuros estudiantes, estudiantes, egresados, profesores y funcionarios) así como a emprendedores interesados en las actividades que ofrecemos."
        },
        {
            "question": "que es ithaka centro emprendimiento ucu que hacen servicios",
            "answer": "Ithaka es el centro de emprendimiento e innovación de la Universidad Católica del Uruguay. Ofrecemos programas educativos, incubadora de startups, mentorías, y capacitaciones para desarrollar el espíritu emprendedor. Estamos abiertos tanto a la comunidad UCU como a emprendedores externos."
        },

        # Costos y accesibilidad
        {
            "question": "¿Cuánto cuestan los cursos y actividades de Ithaka?",
            "answer": "Todas nuestras actividades son completamente gratuitas. Los cursos electivos son gratis para estudiantes UCU que tengan créditos disponibles, las mentorías están abiertas a la comunidad universitaria UCU, y nuestros programas como Fellows incluyen becas completas. Nuestro objetivo es hacer el emprendimiento accesible para todos."
        },
        {
            "question": "costo precio gratis gratuito pagar actividades cursos mentoria",
            "answer": "¡Todo es gratuito! En Ithaka creemos que el emprendimiento debe ser accesible. Nuestros cursos, mentorías, programas y actividades de incubadora no tienen costo. Solo necesitas ganas de aprender y emprender. Para estudiantes UCU solo se requieren créditos disponibles para cursos electivos."
        },

        # Convocatorias y novedades
        {
            "question": "¿Cómo me entero de las convocatorias y novedades de Ithaka?",
            "answer": "Puedes seguirnos en nuestras redes sociales (Instagram, Twitter y LinkedIn) o suscribirte a nuestro newsletter. Allí publicamos todas las convocatorias, eventos, y oportunidades disponibles."
        },
        {
            "question": "noticias convocatorias eventos novedades informacion contacto redes",
            "answer": "Para estar al día con Ithaka, síguenos en Instagram, Twitter y LinkedIn. También tenemos un newsletter donde enviamos todas las oportunidades, convocatorias y eventos. Así no te pierdes ninguna oportunidad de crecimiento emprendedor."
        },

        # Minor de emprendimiento
        {
            "question": "¿Qué ofrece el minor de emprendimiento?",
            "answer": "Este programa de un semestre te permite especializarte en creatividad, innovación y mentalidad emprendedora. Desarrollarás la capacidad de detectar problemáticas y proponer soluciones, creando modelos de negocios innovadores y sustentables. https://minor-innovacion-emprend-6ucsomp.gamma.site/"
        }
    ]

    async for session in get_async_session():
        for i, faq_data in enumerate(FAQS_DATA, 1):
            print(
                f"📝 Procesando FAQ {i}/{len(FAQS_DATA)}: {faq_data['question'][:50]}...")

            try:
                # Crear embedding y guardar FAQ
                new_faq = await embedding_service.add_faq_embedding(
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    session=session
                )

                if new_faq:
                    print(f"   ✅ FAQ agregada con ID: {new_faq.id}")
                else:
                    print(f"   ❌ Error agregando FAQ {i}")

            except Exception as e:
                print(f"   ❌ Error procesando FAQ {i}: {e}")

        break  # Solo necesitamos una iteración

    print("\n✅ FAQs cargadas exitosamente")
    print(f"📊 Total de FAQs procesadas: {len(FAQS_DATA)}")


async def main():
    """Función principal"""
    try:
        await populate_faqs()
        print("\n🎉 ¡Población de FAQs completada exitosamente!")
    except Exception as e:
        print(f"\n❌ Error durante la población de FAQs: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
