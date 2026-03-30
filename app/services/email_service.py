# app/services/email_service.py
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings


def send_otp_email(to_email: str, otp: str, first_name: str) -> None:
    """Send a password reset OTP email."""
    _send_email(
        to_email=to_email,
        subject="Votre code de réinitialisation — NurseLink",
        html=_build_otp_html(
            first_name=first_name,
            otp=otp,
            title="Réinitialisation du mot de passe",
            body_text=(
                "Vous avez demandé à réinitialiser votre mot de passe.<br>"
                f"Utilisez le code ci-dessous — il est valable "
                f"<strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>."
            ),
        ),
    )


def send_verification_email(to_email: str, otp: str, first_name: str) -> None:
    """Send an email address verification OTP email."""
    _send_email(
        to_email=to_email,
        subject="Vérifiez votre adresse email — NurseLink",
        html=_build_otp_html(
            first_name=first_name,
            otp=otp,
            title="Vérification de l'email",
            body_text=(
                "Bienvenue sur NurseLink ! Pour activer votre compte,<br>"
                f"entrez le code ci-dessous — il est valable "
                f"<strong>{settings.OTP_EXPIRE_MINUTES} minutes</strong>."
            ),
        ),
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, html: str) -> None:
    """Core SMTP sender — raises on failure."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM, to_email, msg.as_string())


def _build_otp_html(
    first_name: str,
    otp: str,
    title: str,
    body_text: str,
) -> str:
    return f"""
    <html>
      <body style="margin:0;padding:0;background:#f4f6fb;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
          <tr>
            <td align="center">
              <table width="480" cellpadding="0" cellspacing="0"
                     style="background:#ffffff;border-radius:16px;
                            box-shadow:0 4px 24px rgba(0,0,0,0.08);overflow:hidden;">

                <!-- Header -->
                <tr>
                  <td style="background:linear-gradient(135deg,#3b6cf8,#6a9af7);
                             padding:32px 40px;text-align:center;">
                    <h1 style="margin:0;color:#ffffff;font-size:24px;
                               font-weight:800;letter-spacing:-0.5px;">
                      NurseLink
                    </h1>
                    <p style="margin:6px 0 0;color:rgba(255,255,255,0.75);font-size:13px;">
                      Plateforme de soins infirmiers à domicile
                    </p>
                  </td>
                </tr>

                <!-- Body -->
                <tr>
                  <td style="padding:40px;">
                    <h2 style="margin:0 0 4px;color:#1a1a2e;font-size:18px;">
                      {title}
                    </h2>
                    <h3 style="margin:0 0 20px;color:#3b6cf8;font-size:15px;
                               font-weight:400;">
                      Bonjour {first_name} 👋
                    </h3>
                    <p style="margin:0 0 28px;color:#555;font-size:14px;line-height:1.6;">
                      {body_text}
                    </p>

                    <!-- OTP box -->
                    <div style="background:#f0f4ff;border-radius:12px;
                                padding:28px;text-align:center;margin-bottom:28px;">
                      <span style="font-size:44px;font-weight:900;
                                   letter-spacing:14px;color:#3b6cf8;
                                   font-family:'Courier New',monospace;">
                        {otp}
                      </span>
                    </div>

                    <p style="margin:0 0 6px;color:#888;font-size:13px;">
                      ⚠️ Ne partagez jamais ce code avec quelqu'un.
                    </p>
                    <p style="margin:0;color:#888;font-size:13px;">
                      Si vous n'avez pas fait cette demande, ignorez cet email —
                      votre compte est en sécurité.
                    </p>
                  </td>
                </tr>

                <!-- Footer -->
                <tr>
                  <td style="background:#f9fafb;padding:20px 40px;
                             border-top:1px solid #eee;text-align:center;">
                    <p style="margin:0;color:#bbb;font-size:12px;">
                      © 2025 NurseLink. Tous droits réservés.
                    </p>
                  </td>
                </tr>

              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """