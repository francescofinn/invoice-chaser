import resend

from database import settings

DEFAULT_FROM_ADDRESS = "Invoice Chaser <onboarding@resend.dev>"

resend.api_key = settings.resend_api_key


def _render_html(
    client_name: str,
    body_text: str,
    payment_link: str,
    invoice_number: str,
    amount: str,
    due_date: str,
    is_overdue: bool = False,
) -> str:
    if is_overdue:
        hero_bg       = "#1a0a0a"
        hero_accent   = "#ef4444"
        hero_glow     = "rgba(239,68,68,0.35)"
        badge_bg      = "#3f1515"
        badge_color   = "#fca5a5"
        badge_label   = "OVERDUE"
        btn_bg        = "#ef4444"
        btn_hover_bg  = "#dc2626"
        amount_color  = "#fca5a5"
    else:
        hero_bg       = "#0f172a"
        hero_accent   = "#6366f1"
        hero_glow     = "rgba(99,102,241,0.35)"
        badge_bg      = "#1e1b4b"
        badge_color   = "#a5b4fc"
        badge_label   = "PAYMENT DUE"
        btn_bg        = "#6366f1"
        btn_hover_bg  = "#4f46e5"
        amount_color  = "#e0e7ff"

    paragraphs = "".join(
        f"<p style='margin:0 0 16px 0;color:#374151;font-size:15px;line-height:1.7;'>{line}</p>"
        for line in body_text.strip().split("\n")
        if line.strip()
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1.0" />
  <title>Invoice {invoice_number}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

<table width="100%" cellpadding="0" cellspacing="0" role="presentation"
       style="background:#f1f5f9;padding:48px 16px 64px;">
  <tr>
    <td align="center">
      <table width="580" cellpadding="0" cellspacing="0" role="presentation"
             style="max-width:580px;width:100%;">

        <!-- ── Logo bar ───────────────────────────────────────────── -->
        <tr>
          <td style="padding-bottom:28px;text-align:center;">
            <table cellpadding="0" cellspacing="0" role="presentation"
                   style="display:inline-table;">
              <tr>
                <td style="background:#0f172a;border-radius:10px;padding:10px 18px;">
                  <span style="font-size:15px;font-weight:700;color:#ffffff;
                               letter-spacing:0.3px;white-space:nowrap;">
                    ⚡ Invoice Chaser
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Hero card ──────────────────────────────────────────── -->
        <tr>
          <td style="background:{hero_bg};border-radius:16px 16px 0 0;
                     padding:40px 40px 36px;position:relative;overflow:hidden;">

            <!-- Glow blob (purely decorative — ignored by most clients) -->
            <div style="position:absolute;top:-60px;right:-60px;width:220px;height:220px;
                        background:{hero_glow};border-radius:50%;filter:blur(60px);
                        pointer-events:none;"></div>

            <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
              <tr>
                <td valign="top">
                  <!-- Badge -->
                  <span style="display:inline-block;background:{badge_bg};color:{badge_color};
                               font-size:10px;font-weight:700;letter-spacing:1.2px;
                               padding:4px 12px;border-radius:20px;
                               text-transform:uppercase;margin-bottom:20px;">
                    {badge_label}
                  </span>

                  <!-- Amount -->
                  <div style="font-size:13px;color:#94a3b8;letter-spacing:0.4px;
                              margin-bottom:6px;text-transform:uppercase;">
                    Amount Due
                  </div>
                  <div style="font-size:44px;font-weight:800;color:{amount_color};
                              letter-spacing:-1.5px;line-height:1;margin-bottom:20px;">
                    ${amount}
                  </div>

                  <!-- Divider -->
                  <div style="height:1px;background:rgba(255,255,255,0.08);
                              margin-bottom:20px;"></div>

                  <!-- Invoice # + Due date row -->
                  <table width="100%" cellpadding="0" cellspacing="0" role="presentation">
                    <tr>
                      <td width="50%" style="vertical-align:top;">
                        <div style="font-size:11px;color:#64748b;letter-spacing:0.4px;
                                    text-transform:uppercase;margin-bottom:4px;">Invoice</div>
                        <div style="font-size:15px;font-weight:600;color:#e2e8f0;">
                          {invoice_number}
                        </div>
                      </td>
                      <td width="50%" style="vertical-align:top;text-align:right;">
                        <div style="font-size:11px;color:#64748b;letter-spacing:0.4px;
                                    text-transform:uppercase;margin-bottom:4px;">Due Date</div>
                        <div style="font-size:15px;font-weight:600;color:#e2e8f0;">
                          {due_date}
                        </div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- ── Body card ──────────────────────────────────────────── -->
        <tr>
          <td style="background:#ffffff;padding:36px 40px 20px;">
            {paragraphs}
          </td>
        </tr>

        <!-- ── CTA card ───────────────────────────────────────────── -->
        <tr>
          <td style="background:#ffffff;padding:4px 40px 40px;
                     border-radius:0 0 16px 16px;text-align:center;">

            <!-- Button -->
            <a href="{payment_link}"
               style="display:inline-block;background:{btn_bg};color:#ffffff;
                      font-size:16px;font-weight:700;text-decoration:none;
                      padding:16px 48px;border-radius:10px;
                      letter-spacing:0.2px;margin-bottom:20px;">
              Pay Now &rarr;
            </a>

            <!-- Divider -->
            <div style="height:1px;background:#f1f5f9;margin-bottom:20px;"></div>

            <!-- Fallback link -->
            <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.6;">
              Button not working?<br>
              <a href="{payment_link}"
                 style="color:#6366f1;word-break:break-all;">{payment_link}</a>
            </p>
          </td>
        </tr>

        <!-- ── Spacer ─────────────────────────────────────────────── -->
        <tr><td style="height:16px;"></td></tr>

        <!-- ── Footer ────────────────────────────────────────────── -->
        <tr>
          <td style="text-align:center;font-size:12px;color:#94a3b8;line-height:1.7;
                     padding:0 24px;">
            Sent by <strong style="color:#64748b;">Invoice Chaser</strong>
            on behalf of your service provider.<br>
            If you received this in error, please ignore it.
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>

</body>
</html>"""


def send_invoice_email(
    to_email: str,
    subject: str,
    body: str,
    payment_link: str,
    invoice_number: str = "",
    amount: str = "",
    due_date: str = "",
    is_overdue: bool = False,
) -> str:
    """Send an invoice email and return the provider message ID."""
    html = _render_html(
        client_name=to_email,
        body_text=body,
        payment_link=payment_link,
        invoice_number=invoice_number,
        amount=amount,
        due_date=due_date,
        is_overdue=is_overdue,
    )
    params = {
        "from": DEFAULT_FROM_ADDRESS,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }
    response = resend.Emails.send(params)
    if isinstance(response, dict):
        return response["id"]
    return response.id
