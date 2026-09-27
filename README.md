# FINTRACK

FINTRACK is een moderne persoonlijke financiële webapp waarmee je inkomsten, uitgaven, beleggingen en spaardoelen centraal opvolgt. De app combineert een financieel dashboard met marktdata, nieuws en een Gemini AI-adviseur.

> **Status:** actief in ontwikkeling. De huidige versie draait als Flask-app met SQLite, Gunicorn en nginx. Multi-user data-isolatie, accountbeheer, adminfuncties en uitgebreide security-hardening zijn aanwezig.

## Belangrijkste functies

- **Dashboard:** inkomsten, uitgaven, netto saldo, spaarpercentage, vermogen en financiële inzichten.
- **Inkomsten & uitgaven:** toevoegen, bekijken, bewerken en verwijderen.
- **Spaardoelen:** doelen aanmaken, bedragen toevoegen, voortgang opvolgen en deadlines bekijken.
- **Beleggen:** portefeuille met actuele marktkoersen waar beschikbaar, gemiddelde aankoopprijs, rendement en review-signalen.
- **Markt & Nieuws:** marktindexen, crypto, valuta, grondstoffen en relevante financiële nieuwsartikelen.
- **AI Adviseur:** Gemini-gebaseerde analyse van financiële situatie, portefeuille, spaardoelen en beleggingsprofiel.
- **FINTRACK 2.0:** koppeling tussen cashflow, spaardoelen, beleggingsportefeuille, risicoprofiel en beleggingshorizon.
- **Account:** profielgegevens, valuta, risicoprofiel, beleggingshorizon, maandbudget en noodfondsdoel.
- **Admin:** gebruikersbeheer, rollen en basisstatistieken voor administrators.
- **Multi-user:** financiële gegevens zijn per account geïsoleerd.
- **Responsive UX:** desktop- en mobiele interface met moderne navigatie en hamburger-menu.
- **Thema:** licht/donker thema dat centraal wordt opgeslagen en over alle pagina's wordt toegepast.
- **Valuta:** gebruikers kunnen EUR, USD of GBP kiezen; bedragen worden waar mogelijk omgerekend met actuele wisselkoersen.
- **Security:** CSRF, rate limiting, veilige cookies, CSP, security headers, trusted hosts en verplichte externe secret key.

## FINTRACK 2.0

FINTRACK probeert financiële onderdelen niet als losse pagina's te behandelen, maar als één geheel.

De financiële context kan bestaan uit:

- inkomsten en uitgaven;
- vrije cashflow;
- spaardoelen en deadlines;
- noodfondsdoel;
- maandelijkse beleggingsruimte;
- risicoprofiel;
- beleggingshorizon;
- huidige portefeuille;
- marktdata en relevant financieel nieuws.

De AI-adviseur kan deze informatie combineren om scenario's, risico's, concentraties en aandachtspunten te bespreken. Bij koop- of verkoopvragen geeft de applicatie geen gegarandeerde handelsorders: analyses zijn bedoeld als ondersteuning bij het beoordelen van posities en risico's.

## AI

FINTRACK gebruikt **Google Gemini** voor de AI-adviseur.

De API-sleutel hoort uitsluitend in de environment-configuratie van de server te staan en nooit in GitHub.

De AI-context kan onder andere bevatten:

- gekozen valuta;
- risicoprofiel;
- beleggingshorizon;
- inkomsten, uitgaven en overschot;
- maandelijkse beleggingsruimte;
- noodfondsdoel;
- spaardoelen;
- portefeuille;
- marktdata;
- relevant financieel nieuws.

## Thema

Het thema wordt centraal opgeslagen via de browserinstelling van FINTRACK. De keuze voor licht of donker wordt daardoor over de verschillende pagina's meegenomen.

De interface is ontworpen rond één consistente visuele stijl voor:

- dashboard;
- inkomsten;
- uitgaven;
- beleggen;
- markt & nieuws;
- AI-adviseur;
- spaardoelen;
- account;
- admin;
- login en registratie.

## Valuta

FINTRACK ondersteunt momenteel:

- EUR — euro
- USD — Amerikaanse dollar
- GBP — Britse pond

Nieuwe inkomsten en uitgaven worden intern in EUR opgeslagen en bij invoer/weergave omgerekend naar de gekozen accountvaluta. Beleggingen bewaren daarnaast hun oorspronkelijke koersvaluta.

> Historische gegevens die vóór de valuta-functionaliteit zijn ingevoerd kunnen een oorspronkelijke valuta niet altijd betrouwbaar identificeren. Controleer oudere transacties na een grote migratie.

## Account en profiel

Per gebruiker kan FINTRACK onder andere bewaren:

- gebruikersnaam;
- weergavenaam;
- e-mailadres;
- voorkeursvaluta;
- avatar-kleur;
- risicoprofiel;
- beleggingshorizon;
- maandelijks beleggingsbudget;
- noodfondsdoel.

Wachtwoorden kunnen vanuit het accountgedeelte worden gewijzigd.

## Admin

De eerste bestaande gebruiker wordt bij de eerste migratie administrator wanneer er nog geen administrator bestaat.

Administrators kunnen:

- gebruikers bekijken;
- administratorrechten toekennen of intrekken;
- gebruikers verwijderen;
- basisstatistieken bekijken.

Een administrator kan zichzelf niet verwijderen of de laatste administratorrol verwijderen.

## Projectstructuur

```text
FinTracker/
├── backend/
│   └── app/
│       ├── app.py
│       ├── database.py
│       ├── models.py
│       └── routes/
├── frontend/
│   ├── *.html
│   └── css/style.css
├── scripts/
│   └── import_excel.py
├── instance/
│   └── expenses.db
├── requirements.txt
├── .gitignore
└── README.md
```

## Technologie

- Python 3.13 in de huidige Raspberry Pi-productieomgeving
- Flask
- Flask-SQLAlchemy
- Flask-Login
- Flask-WTF / CSRF
- Flask-Limiter
- Gunicorn
- SQLite
- nginx
- DuckDNS
- Let's Encrypt / Certbot
- Google Gemini API
- Yahoo Finance-marktdata
- HTML / CSS / JavaScript
- Native SVG charts

## Vereisten

- Python 3.10 of nieuwer
- Virtuele Python-omgeving
- Internetverbinding voor marktdata, nieuws en Gemini
- API-configuratie voor Gemini indien de AI-functies worden gebruikt

## Security

FINTRACK bevat meerdere beveiligingslagen:

- wachtwoorden worden gehasht met Werkzeug;
- CSRF-bescherming op POST-formulieren;
- Secure, HttpOnly en SameSite-cookies;
- beperkte sessieduur;
- rate limiting op gevoelige endpoints;
- CSP met nonce;
- HSTS op HTTPS;
- X-Frame-Options;
- X-Content-Type-Options;
- strikte Referrer-Policy;
- trusted-host-validatie;
- per-gebruiker afscherming van financiële records;
- logout via POST + CSRF;
- secret key buiten de repository;
- veilige redirect-validatie;
- database-migraties die rekening houden met bestaande installaties.

> Security-hardening maakt een webapplicatie niet automatisch onhackbaar. Houd dependencies, Raspberry Pi OS, nginx en de database up-to-date.

## Environment

De productieomgeving gebruikt een environment file buiten de repository.

Minimaal:

```env
FINTRACK_SECRET_KEY=<lange-willekeurige-sleutel>
FINTRACK_TRUSTED_HOSTS=fintrackerjelle.duckdns.org,localhost,127.0.0.1
GEMINI_API_KEY=<gemini-api-key>
```

Genereer bijvoorbeeld een secret key met:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Bewaar secrets nooit in GitHub, HTML-bestanden of Python-broncode.

## Raspberry Pi deployment

De huidige productieomgeving draait op een Raspberry Pi achter nginx en Gunicorn.

Veilige updatevolgorde:

```bash
cd ~/FinTracker
cp instance/expenses.db instance/expenses.db.backup-$(date +%Y%m%d-%H%M%S)
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python -m py_compile backend/app/app.py backend/app/models.py
sudo systemctl restart fintrack
sudo systemctl status fintrack --no-pager
```

Bij problemen:

```bash
sudo journalctl -u fintrack -n 100 --no-pager
curl -I http://127.0.0.1:8000
```

> Maak altijd eerst een databaseback-up. Startupschema-migraties zijn ontworpen om bestaande installaties bij te werken, maar een back-up blijft noodzakelijk.

## Development

Werk in kleine, controleerbare stappen.

Na wijzigingen is het aanbevolen om minimaal te controleren:

1. Python syntax/imports.
2. Login en registratie.
3. Dashboard.
4. De gewijzigde module.
5. Mobiele layout.
6. Licht en donker thema.
7. Database-migraties indien modellen zijn aangepast.
8. AI/marktdata indien die onderdelen zijn gewijzigd.

## GitHub

Repository: `Jelle2003/FinTracker`

De `main` branch bevat de actuele applicatieversie. De Raspberry Pi moet na wijzigingen expliciet worden bijgewerkt met `git pull origin main`; GitHub-wijzigingen zijn dus niet automatisch live op de Raspberry Pi.
