# C.A.R.G. - Generatore Fatture

App web per la generazione di fatture PDF del **Consorzio Acquedotto Rurale Gavonata**.

Deployata su [Streamlit Cloud](https://share.streamlit.io) — accessibile da browser senza installazioni.

## Funzionalità

### Da file CSV
- Caricamento file CSV con i dati dei soci
- Anteprima dei dati caricati
- Generazione fatture per: tutti i soci, intervallo, o soci specifici
- Download singolo PDF o ZIP con tutte le fatture
- Opzione filigrana BOZZA

### Fattura singola
- Form con campi precompilati di esempio
- Dati socio: codice utente, nome, codice fiscale, indirizzo
- Dati fattura: numero, data fattura, termine di pagamento
- Letture contatore: periodo di riferimento, lettura iniziale e finale
- Calcolo automatico: consumo, eccedenza oltre 80 m³, imponibile, IVA 10%, totale
- Download diretto del PDF generato

## Formato CSV

Il file CSV deve usare `;` come separatore e contenere le seguenti colonne:

| Colonna | Descrizione |
|---|---|
| `codice_utente` | Numero identificativo del socio |
| `nome_completo` | Nome e cognome o ragione sociale |
| `indirizzo` | Indirizzo completo |
| `codice_fiscale` | Codice fiscale o partita IVA |
| `nomefile` | Nome per il file PDF |
| `data_lettura_2024` | Periodo lettura iniziale (es. AGOSTO 2024) |
| `m3_lettura_2024` | Lettura contatore iniziale in m³ |
| `data_lettura_2025` | Periodo lettura finale (es. AGOSTO 2025) |
| `m3_lettura_2025` | Lettura contatore finale in m³ |
| `email` | Email del socio (opzionale) |

## Logica di calcolo

- **Canone fisso annuo:** € 130,00 (fino a 80 m³)
- **Eccedenza:** € 1,80/m³ oltre la soglia di 80 m³
- **IVA:** 10% sull'imponibile
- **Numero fattura:** codice_utente + 1

## Deploy

L'app è deployata su Streamlit Cloud. Per aggiornare:

1. Modifica i file nel repository
2. Push su `main`
3. Streamlit Cloud si aggiorna automaticamente

## Requisiti (solo per sviluppo locale)

```
pip install streamlit reportlab
streamlit run streamlit_app.py
```

## Struttura

```
├── streamlit_app.py    # App principale
├── requirements.txt    # Dipendenze per Streamlit Cloud
├── logo.png            # Logo C.A.R.G.
└── .gitignore          # Esclude CSV, dati sensibili
```
