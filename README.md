# FINTRACK

FINTRACK is een moderne persoonlijke financiële webapp waarmee je inkomsten, uitgaven, beleggingen en spaardoelen centraal opvolgt. De app combineert een financieel dashboard met marktdata, nieuws en een Gemini AI-adviseur.

> **Status:** actief in ontwikkeling. De huidige versie draait als Flask-app met SQLite, Gunicorn en nginx. Multi-user data-isolatie, accountbeheer, adminfuncties en uitgebreide security-hardening zijn aanwezig.

## Belangrijkste functies

- **Dashboard:** inkomsten, uitgaven, netto saldo, spaarpercentage, vermogen en financiële inzichten.
- **Inkomsten & uitgaven:** toevoegen, bekijken, bewerken en verwijderen.
- **Spaardoelen:** doelen aanmaken, bedragen toevoegen, voortgang opvolgen, deadlines bekijken en benodigde maandelijkse inleg berekenen.
- **Beleggen:** portefeuille met actuele marktkoersen waar beschikbaar, gemiddelde aankoopprijs, rendement en review-signalen. Het toevoegen van posities gebruikt zoekhulp/autocomplete; het beleggingslogboek heeft dezelfde tickerhulp en een responsive formulier dat binnen de kaart blijft.
- **Markt & Nieuws:** marktindexen, crypto, valuta, grondstoffen en relevante financiële nieuwsartikelen.
- **AI Adviseur:** Gemini-gebaseerde analyse van financiële situatie, portefeuille, spaardoelen en beleggingsprofiel.
- **FINTRACK 2.0:** koppeling tussen cashflow, spaardoelen, beleggingsportefeuille, risicoprofiel en beleggingshorizon.
- **Account:** profielgegevens, valuta, risicoprofiel, beleggingshorizon, maandbudget en noodfondsdoel.
- **Admin:** gebruikersbeheer, rollen en basisstatistieken voor administrators.
- **Multi-user:** financiële gegevens zijn per account geïsoleerd.
- **Responsive UX:** desktop- en mobiele interface met moderne navigatie, hamburger-menu en mobile-first touch targets.
- **Transacties:** gecombineerd overzicht van inkomsten en uitgaven met zoeken, filters, terugkerende patronen en CSV-export van uitsluitend de actieve filterselectie.
- **Alerts:** automatische signalen voor cashflow, spaardoelen, portefeuilleconcentratie en noodfonds.
- **Portfolio analytics:** asset-, sector- en regioverdeling plus een beleggingslogboek voor aankopen, verkopen en dividend.
- **Gedeelde navigatie:** alle ingelogde pagina's gebruiken dezelfde centrale `frontend/_navbar.html`, zodat hoogte, volgorde en UX van de navbar overal identiek blijven.
- **Thema:** licht/donker thema dat centraal wordt opgeslagen en over alle pagina's wordt toegepast.
- **Valuta:** gebruikers kunnen EUR, USD of GBP kiezen; bedragen worden waar mogelijk omgerekend met actuele wisselkoersen.
- **Security:** CSRF, rate limiting, veilige cookies, CSP, security headers, trusted hosts en verplichte externe secret key.


## Gebruikershandleiding — FINTRACK gebruiken

FINTRACK is opgebouwd als één financieel overzicht. De bedoeling is dat je eerst je financiële basis invult en daarna stap voor stap je inkomsten, uitgaven, spaardoelen en vermogen bijhoudt. Hoe vollediger de gegevens, hoe nuttiger het dashboard, de alerts en de AI-adviseur worden.

### 1. Eerste keer starten

1. Open FINTRACK en maak een account aan.
2. Log in.
3. Ga naar **Meer → Account**.
4. Vul indien gewenst je weergavenaam en e-mailadres in.
5. Kies je **voorkeursvaluta**: EUR, USD of GBP.
6. Stel je **risicoprofiel** en **beleggingshorizon** in.
7. Vul je **maandelijkse beleggingsbudget** en **noodfondsdoel** in als je deze functies wilt gebruiken.
8. Kies eventueel je thema en avatar-kleur.

Deze gegevens vormen de persoonlijke context voor verschillende onderdelen van FINTRACK en voor de AI-adviseur.

### 2. Je dashboard begrijpen

**Overzicht** is je startpunt. Hier zie je onder andere:

- inkomsten;
- uitgaven;
- netto saldo;
- spaarpercentage;
- spaardoelen;
- portefeuillewaarde en rendement;
- financiële inzichten;
- recente transacties;
- grafieken.

Gebruik het dashboard vooral als controlecentrum. De onderliggende pagina's zijn bedoeld om gegevens correct in te voeren en uitgebreider te bekijken.

### 3. Inkomsten toevoegen

Ga naar **Financiën → Inkomsten**.

Voeg bijvoorbeeld toe:

- loon;
- vakantiegeld;
- terugbetalingen;
- freelance-inkomsten;
- andere inkomsten.

Vul het bedrag, de datum en de categorie zo correct mogelijk in. Nieuwe bedragen worden volgens je gekozen accountvaluta verwerkt en intern naar EUR omgerekend wanneer dat nodig is.

### 4. Uitgaven toevoegen

Ga naar **Financiën → Uitgaven**.

Registreer je uitgaven zo consequent mogelijk. Denk bijvoorbeeld aan:

- huur of woonkosten;
- boodschappen;
- vervoer;
- abonnementen;
- vrije tijd;
- verzekeringen;
- andere vaste of variabele kosten.

Goede categorieën maken de grafieken, inzichten en alerts veel bruikbaarder.

### 5. Transacties controleren

Ga naar **Financiën → Transacties** om inkomsten en uitgaven samen te bekijken.

Je kunt hier:

- zoeken op omschrijving;
- filteren op type;
- filteren op categorie;
- filteren op begin- en einddatum;
- terugkerende patronen herkennen;
- de huidige selectie exporteren naar CSV.

De CSV-export gebruikt de actieve filters. Je krijgt dus niet automatisch alle transacties wanneer je een selectie hebt gemaakt.

### 6. Spaardoelen instellen

Ga naar **Spaardoelen**.

Maak bijvoorbeeld doelen aan voor:

- noodfonds;
- vakantie;
- auto;
- woning;
- grote aankoop;
- andere persoonlijke doelen.

Geef een doel een naam, doelbedrag en eventueel een deadline. Daarna kun je bedragen toevoegen en de voortgang opvolgen.

FINTRACK berekent bij doelen met een deadline ook hoeveel je ongeveer per maand moet opzijzetten om het resterende bedrag tegen die deadline te bereiken.

**Praktische werkwijze:** gebruik spaardoelen voor geld dat je op een bepaalde termijn nodig hebt. Geld voor een doel op korte termijn hoeft niet automatisch als beleggingsgeld te worden beschouwd.

### 7. Beleggingen toevoegen

Ga naar **Vermogen → Beleggen**.

#### Nieuwe portefeuillepositie

Gebruik de zoekfunctie bij het toevoegen van een belegging.

1. Typ een bedrijfsnaam, fondsnaam of ticker, bijvoorbeeld Apple, AAPL of VWCE.
2. Kies de juiste belegging uit de zoekresultaten.
3. Controleer de geselecteerde naam, ticker en valuta.
4. Vul het aantal en je gemiddelde aankoopprijs in.
5. Kies indien beschikbaar een sector en regio.
6. Klik op **Opslaan**.

De zoekfunctie is bewust belangrijk: typ niet zomaar een ticker uit het hoofd wanneer je niet zeker bent. Door de juiste zoekresultaten te selecteren verklein je de kans dat je een verkeerde belegging registreert.

De actuele koers wordt door FINTRACK opgehaald wanneer marktdata beschikbaar is. Als de koers niet beschikbaar is, wordt dat in de applicatie aangegeven.

### 8. Beleggingslogboek gebruiken

Op de Beleggen-pagina kun je daarnaast activiteiten registreren:

- **Aankoop** — vul aantal en prijs per stuk in;
- **Verkoop** — vul aantal en prijs per stuk in;
- **Dividend** — vul het ontvangen bedrag in.

Bij **Belegging / ticker** kun je de naam of ticker intypen en een resultaat uit de zoekhulp kiezen. Dit is de veiligste manier om de juiste ticker te gebruiken.

De datum en een optionele notitie kunnen extra context geven, bijvoorbeeld maandelijkse aankoop of dividend Q2.

### 9. Portefeuille-analytics lezen

FINTRACK toont naast je posities ook analyses van:

- assetverdeling;
- sectorverdeling;
- regioverdeling;
- rendement;
- ontvangen dividend;
- recente beleggingsactiviteiten.

Bij opvallende rendementen kunnen review-signalen verschijnen. Deze signalen zijn bedoeld om je positie opnieuw te bekijken en zijn geen automatische koop- of verkooporders.

### 10. Markt & Nieuws

Ga naar **Vermogen → Markt & Nieuws**.

Hier vind je onder andere:

- belangrijke beursindexen;
- crypto;
- valuta;
- grondstoffen;
- relevante financiële nieuwsartikelen.

Je kunt nieuws op datum en onderwerp bekijken. Marktdata en nieuws zijn externe gegevens en kunnen vertraagd, tijdelijk niet beschikbaar of onvolledig zijn.

Gebruik deze pagina als informatiebron en controleer belangrijke informatie bij de oorspronkelijke bron voordat je financiële beslissingen neemt.

### 11. Alerts

Ga naar **Meer → Alerts**.

FINTRACK kan aandachtspunten tonen rond bijvoorbeeld:

- uitgaven die hoger zijn dan inkomsten;
- een hoge verhouding van uitgaven tegenover inkomsten;
- spaardoelen waarvan de deadline dichtbij komt;
- verlopen spaardoelen;
- een sterk geconcentreerde portefeuille;
- de verhouding tussen je noodfonds en je ingestelde doel.

Een alert betekent dat iets aandacht verdient; het is geen automatische conclusie dat je iets moet kopen, verkopen of wijzigen.

### 12. AI Adviseur optimaal gebruiken

Ga naar **AI Adviseur**.

De AI kan je financiële gegevens combineren met je profiel, spaardoelen, portefeuille, marktdata en relevant nieuws.

Voor goede antwoorden kun je concrete vragen stellen, bijvoorbeeld:

- Hoe staat mijn financiële situatie ervoor ten opzichte van mijn spaardoelen?
- Welke posities in mijn portefeuille verdienen een extra review en waarom?
- Hoe verhoudt mijn maandelijkse beleggingsbudget zich tot mijn noodfonds en spaardoelen?
- Welke risico's zie je in de spreiding van mijn portefeuille?
- Wat zijn mogelijke scenario's als ik mijn maandelijkse investering verhoog?

De AI is een analyse- en hulpmiddel. Controleer actuele koersen, nieuws en belangrijke financiële informatie altijd zelf. De AI geeft geen gegarandeerde rendementen of automatische handelsorders.

### 13. Account en beveiliging

Gebruik **Meer → Account** om je profiel en wachtwoord te beheren.

FINTRACK gebruikt onder andere:

- gehashte wachtwoorden;
- CSRF-bescherming;
- rate limiting;
- beveiligde cookies;
- security headers;
- per-gebruiker afgeschermde financiële gegevens.

De administrator ziet het beheer onder **Meer → Admin**. Gewone gebruikers zien deze optie niet.

### 14. Een goede dagelijkse/wekelijkse routine

Voor een zo correct mogelijke FINTRACK-administratie:

**Dagelijks of wanneer nodig**
1. Voeg belangrijke inkomsten en uitgaven toe.
2. Registreer beleggingsactiviteiten wanneer je een aankoop, verkoop of dividend ontvangt.

**Wekelijks**
1. Controleer je transacties.
2. Kijk naar Alerts.
3. Controleer je spaardoelen.
4. Bekijk je portefeuille en eventuele review-signalen.

**Maandelijks**
1. Controleer je inkomsten en uitgaven.
2. Kijk naar je vrije cashflow.
3. Controleer of je spaardoelen nog realistisch zijn.
4. Bekijk je beleggingsbudget en portefeuilleverdeling.
5. Gebruik de AI-adviseur voor een bredere analyse.

### 15. Mobiel gebruiken

FINTRACK is responsive ontworpen. Op een smartphone wordt de navigatie automatisch een hamburger-menu.

Dezelfde account en gegevens zijn beschikbaar op desktop en mobiel. Gebruik op mobiel vooral de compacte navigatie en controleer bij lange formulieren of alle velden correct zijn ingevuld voordat je opslaat.

### 16. Belangrijk om te onthouden

FINTRACK werkt het best wanneer de gegevens **actueel, volledig en consequent** worden bijgehouden.

De belangrijkste volgorde is:

**Account instellen → inkomsten/uitgaven bijhouden → spaardoelen instellen → portefeuille registreren → markt & alerts controleren → AI gebruiken voor analyse.**

FINTRACK ondersteunt je bij het begrijpen van je financiële situatie. Het vervangt geen bank, boekhouder, financieel adviseur of officiële marktbron.

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

## UI-architectuur

De ingelogde pagina's gebruiken een gedeelde navigatie-partial in `frontend/_navbar.html`. Hierdoor hoeft de navbar niet meer afzonderlijk in iedere pagina te worden onderhouden en verkleint de kans op verschillen tussen pagina's.

De centrale CSS voor de navigatie staat in `frontend/css/style.css`.

De dashboard- en mobiele UX zijn verder gepolijst met een mobile-first layout: grotere touch targets, stabiele mobiele navigatie, compacte metric cards, responsive dashboardsecties, verbeterde transactieweergave en een beter leesbare portefeuilleweergave. De desktopweergave behoudt dezelfde visuele structuur. De navbar gebruikt vaste afmetingen, consistente spacing en aparte desktop/mobile breakpoints om layout-shifts te voorkomen.

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


## FINTRACK 3.0 modules

De huidige productrichting bevat naast het basisdashboard een centrale Transacties-module met filters, zoekfunctie, terugkerende patronen en CSV-export; een Alerts-module met automatische aandachtspunten; uitgebreidere Beleggen-analytics voor asset-, sector- en regioweging; en een handmatig beleggingslogboek voor aankopen, verkopen en ontvangen dividend. Deze signalen sluiten aan op de bestaande spaardoelen en Gemini AI-context. Alerts en portfolio-signalen zijn gebaseerd op geregistreerde gegevens en zijn geen gegarandeerde financiële voorspellingen of handelsopdrachten.
