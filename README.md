# com_contact — Kontaktní formulář

Kontaktní formulář s admin schránkou, e-mail notifikací a honeypot anti-spam ochranou.

## Frontend

Dostupný na `/{slug}` (výchozí: `/kontakt`, en_GB: `/contact`). Slug lze přepsat v system_settings → route_overrides.

## Admin

`/admin/com_contact` — přijaté zprávy:
- Tučně = nepřečtené
- Tlačítko pro označení jako přečtené
- Smazání zprávy

`/admin/com_contact/settings` — nastavení:
- **Formulář aktivní** — zapnutí/vypnutí
- **E-mail příjemce** — kam odesílat notifikace (vyžaduje SMTP v core)
- **Předpona předmětu** — výchozí `[Kontakt]`
- **Potvrdit odesílateli** — odešle potvrzovací e-mail odesílateli

## Anti-spam

Formulář obsahuje skryté honeypot pole (`website`). Boti ho typicky vyplní a zpráva je potichu zahozena.

## Vývoj a testy

```bash
cd component/com_contact
pip install -e ".[dev]"
pytest -q
```
