import resend

from database import settings

DEFAULT_FROM_ADDRESS = "Invoice Chaser <invoices@yourdomain.com>"

resend.api_key = settings.resend_api_key


def send_invoice_email(to_email: str, subject: str, body: str, payment_link: str) -> str:
    """Send an invoice email and return the provider message ID."""

    html = body.replace("\n", "<br>")
    params = {
        "from": DEFAULT_FROM_ADDRESS,
        "to": [to_email],
        "subject": subject,
        "html": f"{html}<br><br><a href='{payment_link}'>Pay Now -&gt;</a>",
    }
    response = resend.Emails.send(params)
    if isinstance(response, dict):
        return response["id"]
    return response.id
