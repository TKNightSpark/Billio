import os
import zipfile
import shutil
import subprocess
from jinja2 import Template
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, send_file, render_template

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
app = Flask(__name__, template_folder=TEMPLATE_DIR)

# Helper functions
def round_down_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

def convert_html_date_to_display(html_date_str, html_time_str):
    """Convert HTML date (YYYY-MM-DD) and time (HH:MM) to display format (DD/MM/YY HH:MM)"""
    try:
        # Parse the HTML date and time
        date_obj = datetime.strptime(html_date_str, "%Y-%m-%d")
        time_obj = datetime.strptime(html_time_str, "%H:%M").time()
        
        # Combine date and time
        combined_datetime = datetime.combine(date_obj.date(), time_obj)
        
        # Format for display
        return combined_datetime.strftime("%d/%m/%y %H:%M")
    except (ValueError, TypeError):
        # Fallback to current time if parsing fails
        return datetime.now().strftime("%d/%m/%y %H:%M")

def render_odt_template(template_path, output_odt_path, context):
    temp_dir = os.path.join(os.path.dirname(output_odt_path), "temp_odt")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    try:
        with zipfile.ZipFile(template_path, 'r') as zin:
            zin.extractall(temp_dir)
        
        content_xml_path = os.path.join(temp_dir, "content.xml")
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            content_template = Template(f.read())
        
        rendered_content = content_template.render(context)
        
        with open(content_xml_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)
        
        shutil.make_archive(output_odt_path.replace('.odt', ''), 'zip', temp_dir)
        os.rename(output_odt_path.replace('.odt', '') + '.zip', output_odt_path)
        shutil.rmtree(temp_dir)
        
        print(f"✅ ODT template rendered successfully: {output_odt_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error rendering ODT template: {e}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False

def convert_to_pdf(odt_path, output_dir):
    try:
        print(f"🔄 Converting ODT to PDF: {odt_path}")
        
        # Check if ODT file exists
        if not os.path.exists(odt_path):
            raise FileNotFoundError(f"ODT file not found: {odt_path}")
        
        result = subprocess.run([
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            odt_path
        ], capture_output=True, text=True, check=True)
        
        print(f"✅ LibreOffice conversion successful")
        print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")
            
        # Check if PDF was actually created
        pdf_name = os.path.basename(odt_path).replace('.odt', '.pdf')
        pdf_path = os.path.join(output_dir, pdf_name)
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF was not created: {pdf_path}")
            
        print(f"✅ PDF created successfully: {pdf_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ LibreOffice conversion failed:")
        print(f"Return code: {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Error in PDF conversion: {e}")
        return False

def get_next_invoice_number(output_dir, year_str):
    year_folder = Path(output_dir) / year_str
    if not year_folder.exists():
        return 1
    pdf_files = list(year_folder.glob("*-2-2_*.pdf"))
    return len(pdf_files) + 1

# Helper route to provide invoice meta
@app.route('/invoice_meta')
def invoice_meta():
    current_time = datetime.now()
    rounded_time = round_down_hour(current_time)
    invoice_date_str = rounded_time.strftime("%Y-%m-%d")
    invoice_time_str = rounded_time.strftime("%H:%M")
    due_date = rounded_time + timedelta(days=7)
    due_date_str = due_date.strftime("%Y-%m-%d")

    year_str = rounded_time.strftime("%Y")
    next_invoice_num = get_next_invoice_number(OUTPUT_DIR, year_str)
    invoice_number_str = f"{next_invoice_num}/2/2"

    return {
        "invoice_number": invoice_number_str,
        "invoice_date": invoice_date_str,
        "invoice_time": invoice_time_str,
        "due_date": due_date_str
    }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            # Read form input
            client_name = request.form.get("kupac", "").strip()
            oib = request.form.get("oib", "").strip()
            address = request.form.get("adresa", "").strip()
            postal_code = request.form.get("posta", "").strip()
            city = request.form.get("grad", "").strip()
            invoice_type = request.form.get("vrsta", "obican").strip()
            invoice_number = request.form.get("broj", "").strip()

            invoice_date = request.form.get("datum")
            invoice_time = request.form.get("vrijeme")
            due_date = request.form.get("rok")

            # Get items arrays
            names = request.form.getlist("naziv[]")
            quantities = request.form.getlist("kolicina[]")
            unit_prices = request.form.getlist("cijena[]")

            print(f"📝 Processing invoice for: {client_name}")
            print(f"📝 Items count: {len(names)}")

            # Process invoice number and dates as backend fallback if missing
            current_time = datetime.now()
            rounded_time = round_down_hour(current_time)
            year_str = rounded_time.strftime("%Y")
            
            if not invoice_number:
                next_num = get_next_invoice_number(OUTPUT_DIR, year_str)
                invoice_number = f"{next_num}/2/2"

            # Convert HTML dates to display format
            if invoice_date and invoice_time:
                invoice_date_display = convert_html_date_to_display(invoice_date, invoice_time)
            else:
                invoice_date_display = rounded_time.strftime("%d/%m/%y %H:%M")

            if due_date:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                due_date_display = due_date_obj.strftime("%d/%m/%y")
            else:
                due_date_obj = rounded_time + timedelta(days=7)
                due_date_display = due_date_obj.strftime("%d/%m/%y")

            # Format price and calculate total
            items = []
            total = 0.0
            for i, (name, qty, price) in enumerate(zip(names, quantities, unit_prices)):
                try:
                    quantity = float(qty)
                    unit_price = float(price)
                    line_total = quantity * unit_price
                    total += line_total
                    
                    item = {
                        "name": name.strip(),
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                        "formatted_unit_price": f"{unit_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", " "),
                        "formatted_line_total": f"{line_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " "),
                    }
                    items.append(item)
                    print(f"✅ Item {i+1}: {name} - {quantity} x {unit_price} = {line_total}")
                    
                except (ValueError, TypeError) as e:
                    print(f"❌ Invalid item {i+1}: {name}, {qty}, {price} - Error: {e}")
                    continue

            formatted_total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
            print(f"💰 Total: {formatted_total} EUR")

            # Sanitize client name for filename
            safe_client_name = client_name.replace(" ", "").replace("/", "_")
            year_folder = Path(OUTPUT_DIR) / year_str
            year_folder.mkdir(parents=True, exist_ok=True)

            pdf_filename = f"{invoice_number.replace('/', '-')}_{safe_client_name}.pdf"
            final_pdf_path = year_folder / pdf_filename

            temp_dir = "/tmp/flask_invoice"
            os.makedirs(temp_dir, exist_ok=True)
            temp_odt_path = os.path.join(temp_dir, "temp_invoice.odt")
            temp_pdf_path = os.path.join(temp_dir, "temp_invoice.pdf")

            # Build context for template variables
            context = {
                "client_name": client_name,
                "oib": oib,
                "address": address,
                "postal_code": postal_code,
                "city": city,
                "invoice_type": invoice_type,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date_display,
                "due_date": due_date_display,
                "due_date_desc": due_date_display,
                "location": "Rijeka",
                "items": items,
                "total": total,
                "formatted_total": formatted_total,
            }

            print("🔄 Rendering ODT template...")
            if not render_odt_template(TEMPLATE_PATH, temp_odt_path, context):
                return "Error: Failed to render ODT template", 500

            print("🔄 Converting ODT to PDF...")
            if not convert_to_pdf(temp_odt_path, temp_dir):
                return "Error: Failed to convert ODT to PDF", 500

            # Check if PDF was created
            if not os.path.exists(temp_pdf_path):
                return f"Error: PDF file not found at {temp_pdf_path}", 500

            # Move to final location
            shutil.move(temp_pdf_path, final_pdf_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            print(f"✅ Invoice created successfully: {final_pdf_path}")
            return send_file(final_pdf_path, as_attachment=True, download_name=pdf_filename)

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}", 500

    # GET serve the form
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
