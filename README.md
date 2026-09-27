# FINTRACK

FINTRACK is een persoonlijke financiële webapp waarmee je inkomsten, uitgaven en beleggingen kunt opvolgen via een dashboard.

> **Status:** in ontwikkeling. De huidige versie is gebouwd als een Flask-app met templates. Multi-user data-isolatie en een security-hardeninglaag zijn toegevoegd, maar voer vóór productie een gecontroleerde update en securitytest uit.

## Thema

FINTRACK ondersteunt automatisch een **licht en donker thema** op basis van de systeem-/browservoorkeur van het toestel. De lichte variant gebruikt een heldere fintech-interface met voldoende contrast; de bestaande donkere variant blijft beschikbaar wanneer het toestel op donker staat.

## Registratie

De registratie bevat server-side validatie, controle op dubbele gebruikersnamen, een bevestiging van het wachtwoord en directe login na een succesvolle registratie. De browser controleert de wachtwoordbevestiging ook voordat het formulier wordt verzonden.

> **Multi-user:** inkomsten, uitgaven en beleggingen zijn nu gekoppeld aan het ingelogde account. Bij een bestaande SQLite-database wordt tijdens de upgrade automatisch een `user_id` toegevoegd en worden bestaande records aan het eerste bestaande account gekoppeld. Maak altijd een back-up van `expenses.db` vóór een productie-update.

## Functies

- Dashboard met jaaroverzicht, inkomsten, uitgaven, netto saldo en spaarpercentage.
- Inkomsten en uitgaven toevoegen, bekijken, bewerken en verwijderen.
- Beleggingsportefeuille met marktwaardeschatting en koersen waar beschikbaar.
- Markt- en nieuwspagina en AI-adviseur (afhankelijk van de ingestelde externe diensten).
- Inloggen en accountregistratie.

## Projectstructuur (huidige repository)

```text
FinTracker/
├── backend/
│   └── app/
│       ├── app.py          # Flask-app, routes en applicatielogica
│       ├── database.py     # SQLAlchemy database-extensie
│       ├── models.py       # User, Expense, Income en Investment
│       └── routes/         # Voorbereide map voor verdere opsplitsing
├── frontend/
│   ├── *.html              # Jinja2-pagina's
│   └── css/style.css       # Styling
├── scripts/
│   └── import_excel.py     # Voorziene plek voor Excel-import
├── .gitignore
└── README.md
```

## Vereisten

- Python 3.10 of nieuwer (de productieomgeving kan een andere ondersteunde versie gebruiken).
- De Python-pakketten die de app importeert. Installeer ze in een virtuele omgeving en voeg ontbrekende pakketten toe aan `requirements.txt` wanneer nodig.
- Voor externe AI- of koersdiensten kunnen API-sleutels of netwerktoegang vereist zijn.

## Veiligheid en gegevens

FINTRACK bevat meerdere lagen die bedoeld zijn om veelvoorkomende webaanvallen te beperken:

- Wachtwoorden worden niet in platte tekst opgeslagen; Werkzeug gebruikt een adaptieve password-hash met unieke salt.
- CSRF-bescherming is actief op POST-formulieren, inclusief login, registratie, transacties, beleggingen, AI en uitloggen.
- Sessiecookies zijn `Secure`, `HttpOnly` en `SameSite=Lax` en de sessieduur is beperkt.
- Login, registratie, AI en beleggingzoekopdrachten hebben rate limiting om geautomatiseerde misbruikpogingen af te remmen.
- Security headers worden server-side toegevoegd, waaronder HSTS op HTTPS, CSP, X-Frame-Options, nosniff en een strikte Referrer-Policy.
- Host-header-validatie is ingeschakeld via `TRUSTED_HOSTS`.
- Financiële records zijn per ingelogd account afgeschermd. Een gebruiker kan records van een andere gebruiker niet via een ID ophalen, wijzigen of verwijderen.
- De logout-actie gebruikt POST + CSRF in plaats van een GET-link.
- De Flask-secret-key staat niet meer in de broncode. De applicatie weigert te starten wanneer `FINTRACK_SECRET_KEY` ontbreekt of te kort is.
- Bewaar API-sleutels en andere geheimen uitsluitend buiten GitHub, bijvoorbeeld in een root-only environment file op de Raspberry Pi.
- Maak een back-up van de SQLite-database vóór updates of schemawijzigingen. De bestaande startup-migratie koppelt legacy-records aan het eerste bestaande account.

### Secret key instellen

Genereer op de Raspberry Pi een willekeurige sleutel en bewaar die buiten de repository:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Plaats die waarde bijvoorbeeld in een bestand buiten `~/FinTracker`, met alleen leesrechten voor de servicegebruiker. Configureer daarnaast:

```FINTRACK_SECRET_KEY=<lange-willekeurige-sleutel>
FINTRACK_TRUSTED_HOSTS=fintrackerjelle.duckdns.org,localhost,127.0.0.1
```

Voor rate limiting kan later een gedeelde opslag zoals Redis worden ingesteld via `FINTRACK_RATE_LIMIT_STORAGE`. De standaard `memory://`-opslag is vooral geschikt voor de huidige kleine single-serveropstelling.

> **Belangrijk:** security-hardening vermindert het risico maar maakt geen webapplicatie "onhackbaar". Houd Flask, dependencies, Raspberry Pi OS, nginx en de database up-to-date en test wijzigingen eerst buiten productie.

## Raspberry Pi deployment

De huidige installatie wordt gehost op een Raspberry Pi achter nginx en Gunicorn. Omdat de app nu een externe secret vereist, moet de systemd-service die environment file laden vóór de eerste restart. Maak eerst een databaseback-up en installeer de nieuwe dependencies.

Een veilige updatevolgorde is:

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

Voer deze stappen pas uit nadat je een databaseback-up hebt gemaakt en de wijziging op de Pi hebt gecontroleerd. Bij een fout, bekijk de service-log:

```bash
sudo journalctl -u fintrack -n 100 --no-pager
```

## Bijdragen / ontwikkeling

Werk in kleine, controleerbare stappen. Test na elke wijziging minimaal het importeren van de Flask-app, de login/registratie en de pagina's die zijn aangepast. Test databasewijzigingen eerst op een kopie van de database, niet op de enige productie-database.
