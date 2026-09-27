# FINTRACK

FINTRACK is een persoonlijke financiële webapp waarmee je inkomsten, uitgaven en beleggingen kunt opvolgen via een dashboard.

> **Status:** in ontwikkeling. De huidige versie is gebouwd als een Flask-app met templates. Niet alle onderdelen zijn al geschikt voor meerdere gebruikers.

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

- Bewaar wachtwoorden niet als platte tekst; FINTRACK slaat een wachtwoordhash op.
- Zet geheime sleutels en API-sleutels in omgevingsvariabelen of een niet-gecommitteerd `.env`-bestand. Plaats ze nooit in HTML, JavaScript of GitHub.
- De huidige applicatie gebruikt één SQLite-database en de financiële modellen hebben nog geen eigenaar-koppeling. **Gebruik de registratie daarom voorlopig niet om andere personen toegang te geven:** gebruikers kunnen anders elkaars transacties zien. Eerst is een databasewijziging nodig waarbij iedere transactie aan een gebruiker wordt gekoppeld, inclusief een veilige migratie van bestaande gegevens.
- Maak een back-up van de SQLite-database vóór updates of schemawijzigingen. `db.create_all()` maakt ontbrekende tabellen aan, maar migreert bestaande tabellen/kolommen niet automatisch.
- De Flask-secret-key moet vóór publiek gebruik worden vervangen door een lange, willekeurige geheime waarde die buiten de repository wordt bewaard.

## Raspberry Pi deployment

De huidige installatie wordt gehost op een Raspberry Pi achter nginx en Gunicorn. Na het ophalen van een gecontroleerde wijziging kan de service doorgaans worden bijgewerkt met:

```bash
cd ~/FinTracker
git pull origin main
sudo systemctl restart fintrack
sudo systemctl status fintrack --no-pager
```

Voer deze stappen pas uit nadat je een databaseback-up hebt gemaakt en de wijziging op de Pi hebt gecontroleerd. Bij een fout, bekijk de service-log:

```bash
sudo journalctl -u fintrack -n 100 --no-pager
```

## Bijdragen / ontwikkeling

Werk in kleine, controleerbare stappen. Test na elke wijziging minimaal het importeren van de Flask-app, de login/registratie en de pagina's die zijn aangepast. Test databasewijzigingen eerst op een kopie van de database, niet op de enige productie-database.
