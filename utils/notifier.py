import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()


def send_whatsapp_message(to_phone: str, message: str):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_whatsapp = os.getenv("TWILIO_WHATSAPP_NUMBER")

    client = Client(account_sid, auth_token)
    client.messages.create(
        body=message,
        from_=from_whatsapp,
        to=f"whatsapp:{to_phone}",
    )


def send_email_confirmation(to_email: str, nombre: str = "emprendedor"):
    subject = "✅ Confirmación de postulación - Ithaka"
    body = f"""
    Hola {nombre},

    ¡Gracias por postularte a Ithaka! 🎉

    Recibimos correctamente tu formulario de postulación a través del asistente conversacional. Nuestro equipo revisará tu propuesta y, en caso de avanzar, nos pondremos en contacto contigo por este medio.

    Mientras tanto, podés encontrar más recursos y herramientas para emprendedores en:
    https://www.ucu.edu.uy/categoria/Ithaka-340

    ¡Te deseamos muchos éxitos!

    — Centro Ithaka
    """

    msg = MIMEMultipart()
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.send_message(msg)
            print(f"Correo enviado a {to_email}")
    except Exception as e:
        print(f"Error al enviar correo a {to_email}: {e}")
