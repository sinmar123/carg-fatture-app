import csv
import re
import io
import os
import zipfile
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

# --- Font setup ---
FONT_NAME = 'Helvetica'
FONT_PATHS = [
    'Arial.ttf',
    os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf'),
    '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
]
for fp in FONT_PATHS:
    if os.path.exists(fp):
        try:
            pdfmetrics.registerFont(TTFont('Arial', fp))
            FONT_NAME = 'Arial'
            break
        except Exception:
            pass


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def format_address(indirizzo):
    indirizzo = indirizzo.strip()
    match = re.search(r'\b(\d{5})\s+([A-Z]+(?:\s+[A-Z]+)*)\b', indirizzo)
    if match:
        cap_citta = match.group(0)
        indirizzo_via = indirizzo[:match.start()].strip()
        return [indirizzo_via, cap_citta]
    else:
        return [indirizzo]


def is_partita_iva(codice):
    return codice.isdigit() and len(codice) == 11


class WatermarkCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.add_watermark = kwargs.pop('add_watermark', False)
        canvas.Canvas.__init__(self, *args, **kwargs)

    def showPage(self):
        if self.add_watermark:
            self.saveState()
            self.setFont(FONT_NAME, 100)
            self.setFillColorRGB(0.9, 0.9, 0.9)
            self.translate(A4[0] / 2, A4[1] / 2)
            self.rotate(45)
            self.drawCentredString(0, 0, "BOZZA")
            self.restoreState()
        canvas.Canvas.showPage(self)


def create_pdf_bytes(data, add_watermark=False, logo_bytes=None):
    """Genera il PDF e restituisce i bytes."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2 * cm, leftMargin=2 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    story = []

    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontName = FONT_NAME
    normal_style.fontSize = 9

    title_style = ParagraphStyle('Title', parent=normal_style, fontSize=20,
                                  textColor=colors.HexColor('#1f4788'), fontName='Helvetica-Bold')
    invoice_num_style = ParagraphStyle('InvoiceNum', parent=normal_style,
                                       fontSize=11, alignment=2, textColor=colors.grey)
    total_style = ParagraphStyle('Total', parent=normal_style, fontSize=24,
                                  fontName='Helvetica-Bold', alignment=2, textColor=colors.grey)

    # === HEADER ===
    if logo_bytes:
        logo_buf = io.BytesIO(logo_bytes)
        logo = Image(logo_buf, width=4 * cm, height=4 * cm, kind='proportional')
    elif os.path.exists('logo.png'):
        logo = Image('logo.png', width=4 * cm, height=4 * cm, kind='proportional')
    else:
        logo = Paragraph("<b><font size=20 color='#1f4788'>C.A.R.G.</font></b>", normal_style)

    company_info = Paragraph(
        "Consorzio Acquedotto Rurale Gavonata<br/>"
        "Strada Verzenasco 39 - 15016 Fraz. Gavonata (AL)<br/>"
        "P.iva & C.F. 01751310069<br/>"
        "tel. 3717766135<br/>"
        "cargavonata@gmail.com",
        ParagraphStyle('CompanyInfo', parent=normal_style, fontSize=9, alignment=2)
    )

    invoice_header = Paragraph(
        f"<b><font size=11 color='grey'>FATTURA nr. {data.get('numero_fattura', 'N/A')}/2025 del 20/10/2025</font></b>",
        invoice_num_style
    )

    header_table = Table([[logo, company_info]], colWidths=[doc.width * 0.5, doc.width * 0.5])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))

    story.append(header_table)
    story.append(invoice_header)
    story.append(Spacer(1, 0.8 * cm))

    # === MITTENTE / DESTINATARIO ===
    story.append(Spacer(1, 0.3 * cm))

    codice_utente = data.get('codice_utente', 'N/A')
    codice = data.get('codice_fiscale', 'N/A')
    is_company = is_partita_iva(codice)

    mittente_text = (
        "<font size=8 color='grey'><b>P.IVA</b> IT01751310069<br/>"
        "<b>CF</b> 01751310069</font>"
    )
    mittente = Paragraph(mittente_text, normal_style)

    indirizzo_lines = '<br/>'.join(data.get('indirizzo_formattato', [data.get('indirizzo', '')]))
    codice_fiscale_label = "P. IVA" if is_company else "Cod. Fisc."

    destinatario_text = (
        f"<font size=8 color='grey'><b>DESTINATARIO</b></font><br/>"
        f"<b>{data.get('nome_completo', 'N/A')}</b><br/>"
        f"{indirizzo_lines}<br/>"
        f"{codice_fiscale_label} {codice}"
    )
    destinatario = Paragraph(destinatario_text, normal_style)

    client_table = Table([[mittente, destinatario]], colWidths=[doc.width * 0.60, doc.width * 0.40])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
    ]))

    story.append(client_table)
    story.append(Spacer(1, 0.8 * cm))

    # === CALCOLI ===
    lettura_2025 = safe_int(data.get('m3_lettura_2025', 0))
    lettura_2024 = safe_int(data.get('m3_lettura_2024', 0))
    consumo = max(0, lettura_2025 - lettura_2024)
    eccedenza = max(0, consumo - 80)
    importo_eccedenza = eccedenza * 1.8
    totale_imponibile = 130 + importo_eccedenza
    iva = totale_imponibile * 0.1
    totale = totale_imponibile + iva

    nome_completo = data.get('nome_completo', 'N/A')
    numero_fattura = data.get('numero_fattura', 'N/A')
    causale = f"CONSUMI PERIODO 2024-2025 - {nome_completo.upper()} - SOCIO {codice_utente} - FATTURA {numero_fattura}"

    # === TABELLA SERVIZI ===
    table_data = [['DESCRIZIONE', 'QUANTITA\'', 'PREZZO UNITARIO', 'IMPORTO']]

    desc_consumi = (
        f"<font size=10>Lettura {data.get('data_lettura_2025', 'N/A').lower()}: {lettura_2025} m\u00b3 | "
        f"Lettura {data.get('data_lettura_2024', 'N/A').lower()}: {lettura_2024} m\u00b3 | "
        f"<b>Consumo totale: {consumo} m\u00b3</b>"
    )
    if eccedenza > 0:
        desc_consumi += f" (di cui {eccedenza} m\u00b3 oltre soglia 80 m\u00b3)</font>"
    else:
        desc_consumi += f" (entro soglia 80 m\u00b3)</font>"

    table_data.append([Paragraph(desc_consumi, normal_style), '', '', ''])

    desc_canone = "<font size=10>Canone annuo fisso per consumo acqua potabile fino a 80 m\u00b3</font>"
    table_data.append([Paragraph(desc_canone, normal_style), '1', '\u20ac 130,00', '\u20ac 130,00'])

    if eccedenza > 0:
        desc_eccedenza = "<font size=10>Conguaglio per eccedenza oltre 80 m\u00b3 (\u20ac1,80/m\u00b3)</font>"
        table_data.append([
            Paragraph(desc_eccedenza, normal_style),
            f'{eccedenza} m\u00b3',
            '\u20ac 1,80',
            f'\u20ac {importo_eccedenza:.2f}'
        ])
    else:
        desc_no_eccedenza = "<font size=10>Nessun conguaglio - consumo entro 80 m\u00b3</font>"
        table_data.append([
            Paragraph(desc_no_eccedenza, normal_style),
            '-', '-', '\u20ac 0,00'
        ])

    services_table = Table(table_data, colWidths=[doc.width * 0.50, doc.width * 0.15, doc.width * 0.17, doc.width * 0.18])
    table_styles = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a4a4a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_styles.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f5f5')))

    services_table.setStyle(TableStyle(table_styles))
    story.append(services_table)
    story.append(Spacer(1, 0.5 * cm))

    # === TOTALI ===
    totali_data = [
        ['', 'Imponibile', f'\u20ac {totale_imponibile:.2f}'],
        ['', 'Totale IVA (10%)', f'\u20ac {iva:.2f}'],
        ['', '', ''],
        ['', Paragraph('<b>TOTALE</b>', total_style),
         Paragraph(f'<b>\u20ac {totale:.2f}</b>', total_style)],
    ]
    totali_table = Table(totali_data, colWidths=[doc.width * 0.5, doc.width * 0.25, doc.width * 0.25])
    totali_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (1, 1), FONT_NAME),
        ('FONTSIZE', (1, 0), (1, 1), 9),
        ('TEXTCOLOR', (1, 0), (2, 1), colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(totali_table)
    story.append(Spacer(1, 1.5 * cm))

    # === SCADENZA ===
    scadenze_text = (
        "<b><font size=10>SCADENZA</font></b><br/>"
        "<font size=10 color='red'><b>31/10/2025</b></font>"
    )
    story.append(Paragraph(scadenze_text, ParagraphStyle('Scadenze', parent=normal_style, alignment=2)))
    story.append(Spacer(1, 0.5 * cm))

    # === PAGAMENTO ===
    payment_text = (
        "<font size=11><b>MODALITA\u0300 DI PAGAMENTO</b></font><br/><br/>"
        "<font size=10>Bonifico Bancario Banca Sella - filiale Acqui Terme</font><br/><br/>"
        "<font size=10>IBAN: IT16O0326847940052938107080</font><br/><br/>"
        "<font size=10>Conto: F652938107080</font><br/><br/>"
        f"<font size=10><b>CAUSALE: {causale}</b></font><br/><br/><br/>"
        "<font size=10>Seguir\u00e0 fattura elettronica</font>"
    )
    story.append(Paragraph(payment_text, normal_style))

    if add_watermark:
        doc.build(story, canvasmaker=lambda *args, **kwargs: WatermarkCanvas(*args, add_watermark=True, **kwargs))
    else:
        doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def parse_csv_rows(uploaded_file):
    """Parsa il CSV caricato e restituisce le righe ordinate."""
    content = uploaded_file.getvalue().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content), delimiter=';')
    rows = [row for row in reader if row.get('codice_utente', '').strip()]
    rows.sort(key=lambda x: safe_int(x.get('codice_utente', '0')))
    for row in rows:
        codice_utente = safe_int(row.get('codice_utente', '0'))
        row['numero_fattura'] = codice_utente + 1
        row['indirizzo_formattato'] = format_address(row.get('indirizzo', ''))
    return rows


# =====================================================================
# STREAMLIT APP
# =====================================================================
st.set_page_config(page_title="C.A.R.G. - Generatore Fatture", page_icon="\U0001f4c4", layout="centered")

st.title("C.A.R.G. - Generatore Fatture")
st.caption("Consorzio Acquedotto Rurale Gavonata")

# Logo (se presente nella directory)
logo_bytes = None
if os.path.exists('logo.png'):
    with open('logo.png', 'rb') as f:
        logo_bytes = f.read()

tab_csv, tab_singola = st.tabs(["\U0001f4c1 Da file CSV", "\u270f\ufe0f Fattura singola"])

# =========================
# TAB 1: Da CSV
# =========================
with tab_csv:
    uploaded_file = st.file_uploader("Carica il file CSV dei soci", type=['csv'])

    if uploaded_file:
        rows = parse_csv_rows(uploaded_file)
        st.success(f"Trovati {len(rows)} soci nel file.")

        # Mostra anteprima
        with st.expander("Anteprima dati"):
            preview_data = []
            for r in rows:
                preview_data.append({
                    'Codice': r.get('codice_utente', ''),
                    'Nome': r.get('nome_completo', ''),
                    'Indirizzo': r.get('indirizzo', ''),
                    'Consumo m\u00b3': safe_int(r.get('m3_lettura_2025', 0)) - safe_int(r.get('m3_lettura_2024', 0)),
                })
            st.dataframe(preview_data, use_container_width=True)

        # Modalita selezione
        modalita = st.radio("Quali fatture generare?",
                            ["Tutte", "Intervallo di soci", "Soci specifici"],
                            horizontal=True)

        codici_filtro = None
        if modalita == "Intervallo di soci":
            col1, col2 = st.columns(2)
            with col1:
                socio_da = st.number_input("Dal socio", min_value=1, value=1, step=1)
            with col2:
                socio_a = st.number_input("Al socio", min_value=1, value=10, step=1)
            codici_filtro = [str(i) for i in range(socio_da, socio_a + 1)]
        elif modalita == "Soci specifici":
            opzioni = [f"{r['codice_utente']} - {r['nome_completo']}" for r in rows]
            selezionati = st.multiselect("Seleziona i soci", opzioni)
            codici_filtro = [s.split(' - ')[0].strip() for s in selezionati]

        add_watermark = st.checkbox("Aggiungi filigrana BOZZA")

        if st.button("Genera fatture", type="primary", use_container_width=True):
            if codici_filtro is not None:
                rows_to_process = [r for r in rows if r.get('codice_utente', '').strip() in codici_filtro]
            else:
                rows_to_process = rows

            if not rows_to_process:
                st.warning("Nessun socio trovato con i criteri selezionati.")
            else:
                progress = st.progress(0, text="Generazione in corso...")
                pdf_files = []

                for i, row in enumerate(rows_to_process):
                    fattura_numero = row['numero_fattura']
                    nome_file = row.get('nomefile', '').strip()
                    if nome_file:
                        filename = f"fattura_{fattura_numero}_{nome_file}.pdf"
                    else:
                        filename = f"fattura_{fattura_numero}.pdf"

                    pdf_data = create_pdf_bytes(row, add_watermark=add_watermark, logo_bytes=logo_bytes)
                    pdf_files.append((filename, pdf_data))
                    progress.progress((i + 1) / len(rows_to_process),
                                      text=f"Generata {i + 1}/{len(rows_to_process)}: {filename}")

                progress.empty()
                st.success(f"Generate {len(pdf_files)} fatture!")

                # Se una sola fattura, download diretto
                if len(pdf_files) == 1:
                    fname, fdata = pdf_files[0]
                    st.download_button(
                        f"Scarica {fname}",
                        data=fdata,
                        file_name=fname,
                        mime="application/pdf",
                        use_container_width=True,
                    )
                else:
                    # Crea ZIP con tutte le fatture
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                        for fname, fdata in pdf_files:
                            zf.writestr(fname, fdata)
                    zip_buffer.seek(0)

                    st.download_button(
                        f"Scarica tutte le fatture ({len(pdf_files)} PDF in ZIP)",
                        data=zip_buffer.getvalue(),
                        file_name="fatture.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )

# =========================
# TAB 2: Fattura singola
# =========================
with tab_singola:
    st.subheader("Inserisci i dati del socio")

    with st.form("form_singola"):
        col1, col2 = st.columns(2)
        with col1:
            codice_utente = st.text_input("Codice utente (socio)", value="1")
            nome_completo = st.text_input("Nome e cognome / Ragione sociale", value="")
            codice_fiscale = st.text_input("Codice Fiscale / P.IVA", value="")
            indirizzo = st.text_input("Indirizzo completo", value="",
                                       placeholder="es. Strada Verzenasco 15, 15016 CASSINE (AL)")

        with col2:
            numero_fattura = st.text_input("Numero fattura", value="")
            data_lettura_2024 = st.text_input("Periodo lettura 2024", value="AGOSTO 2024")
            m3_2024 = st.number_input("Lettura m\u00b3 2024", min_value=0, value=0, step=1)
            data_lettura_2025 = st.text_input("Periodo lettura 2025", value="AGOSTO 2025")
            m3_2025 = st.number_input("Lettura m\u00b3 2025", min_value=0, value=0, step=1)

        add_watermark_single = st.checkbox("Aggiungi filigrana BOZZA", key="wm_single")

        submitted = st.form_submit_button("Genera fattura", type="primary", use_container_width=True)

    if submitted:
        if not nome_completo.strip():
            st.error("Inserisci il nome del socio.")
        else:
            # Se numero fattura non specificato, usa codice_utente + 1
            if not numero_fattura.strip():
                numero_fattura = str(safe_int(codice_utente, 0) + 1)

            data = {
                'codice_utente': codice_utente.strip(),
                'nome_completo': nome_completo.strip(),
                'codice_fiscale': codice_fiscale.strip(),
                'indirizzo': indirizzo.strip(),
                'indirizzo_formattato': format_address(indirizzo.strip()),
                'numero_fattura': numero_fattura.strip(),
                'data_lettura_2024': data_lettura_2024.strip(),
                'm3_lettura_2024': m3_2024,
                'data_lettura_2025': data_lettura_2025.strip(),
                'm3_lettura_2025': m3_2025,
            }

            consumo = max(0, m3_2025 - m3_2024)
            eccedenza = max(0, consumo - 80)
            totale_imponibile = 130 + eccedenza * 1.8
            iva = totale_imponibile * 0.1
            totale = totale_imponibile + iva

            # Anteprima calcoli
            st.info(
                f"**Consumo:** {consumo} m\u00b3 | "
                f"**Eccedenza:** {eccedenza} m\u00b3 | "
                f"**Imponibile:** \u20ac {totale_imponibile:.2f} | "
                f"**IVA 10%:** \u20ac {iva:.2f} | "
                f"**Totale:** \u20ac {totale:.2f}"
            )

            pdf_data = create_pdf_bytes(data, add_watermark=add_watermark_single, logo_bytes=logo_bytes)
            filename = f"fattura_{numero_fattura}_{nome_completo.strip()}.pdf"

            st.download_button(
                f"Scarica {filename}",
                data=pdf_data,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
            )
