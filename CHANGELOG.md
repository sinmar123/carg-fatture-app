# Changelog

## 2026-03-15

### Aggiunto
- App Streamlit con due modalità: generazione da CSV e fattura singola
- Tab CSV: caricamento file, anteprima dati, selezione soci (tutti/intervallo/specifici), download PDF singolo o ZIP
- Tab fattura singola: form con tutti i campi per inserimento manuale dati socio
- Campi data fattura e termine di pagamento nel form fattura singola
- Periodo di riferimento letture (campo testo libero, es. "da Agosto 2024 ad Agosto 2025")
- Lettura iniziale e lettura finale al posto dei campi fissi 2024/2025
- Periodo di riferimento visibile nella descrizione consumi in fattura
- Valori di esempio precompilati in tutti i campi del form fattura singola
- Opzione filigrana BOZZA
- Calcolo automatico consumo, eccedenza, imponibile, IVA, totale
- Deploy su Streamlit Cloud (zero installazioni per l'utente finale)

### Corretto
- Accento "MODALITÀ DI PAGAMENTO" non leggibile nel PDF (carattere Unicode combinante sostituito)
