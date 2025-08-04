import os
import zipfile
import shutil
import subprocess
from jinja2 import Template
from datetime import datetime, timedelta
from pathlib import Path

# === Path Setup ===
# Get the parent directory (root of project) since this script is in scripts/
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'templates', 'invoice_template.odt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# === Functions ===

def round_down_hour(dt):
    """Round down datetime to the previous hour."""
    return dt.replace(minute=0, second=0, microsecond=0)

def render_odt_template(template_path, output_odt_path, context):
    temp_dir = os.path.join(os.path.dirname(output_odt_path), "temp_odt")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    try:
        print(f"📂 Extracting ODT template: {template_path}")
        with zipfile.ZipFile(template_path, 'r') as zin:
            zin.extractall(temp_dir)

        content_xml_path = os.path.join(temp_dir, "content.xml")
        print(f"📝 Reading content.xml")
        
        with open(content_xml_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        print(f"🔧 Rendering template with {len(context.get('items', []))} items")
        
        content_template = Template(template_content)
        rendered_content = content_template.render(context)
        
        print("✅ Template rendered successfully")

        with open(content_xml_path, 'w', encoding='utf-8') as f:
            f.write(rendered_content)

        shutil.make_archive(output_odt_path.replace('.odt', ''), 'zip', temp_dir)
        os.rename(output_odt_path.replace('.odt', '') + '.zip', output_odt_path)
        shutil.rmtree(temp_dir)
        
        print(f"✅ ODT created: {output_odt_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error in render_odt_template: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False

def convert_to_pdf(odt_path, output_dir):
    try:
        print(f"🔄 Converting to PDF: {odt_path}")
        
        if not os.path.exists(odt_path):
            raise FileNotFoundError(f"ODT file not found: {odt_path}")
        
        # Check if LibreOffice is available
        try:
            subprocess.run(['soffice', '--version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise Exception("LibreOffice (soffice) not found. Please install LibreOffice.")
        
        result = subprocess.run([
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            odt_path
        ], capture_output=True, text=True, timeout=30)
        
        print(f"LibreOffice exit code: {result.returncode}")
        if result.stdout:
            print(f"LibreOffice stdout: {result.stdout}")
        if result.stderr:
            print(f"LibreOffice stderr: {result.stderr}")
        
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
    except subprocess.TimeoutExpired:
        print("❌ LibreOffice conversion timed out")
        return False
    except Exception as e:
        print(f"❌ Error in PDF conversion: {e}")
        return False

def get_next_invoice_number(output_dir, year_str):
    """
    Count existing invoice PDFs in the year folder and return the next invoice number.
    """
    year_folder = Path(output_dir) / year_str
    if not year_folder.exists():
        return 1
    pdf_files = list(year_folder.glob("*-2-2_*.pdf"))
    return len(pdf_files) + 1

# === Main Script ===
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 STARTING STANDALONE INVOICE GENERATION")
    print("="*50)
    
    # Debug: Print paths to verify they're correct
    print(f"📁 BASE_DIR: {BASE_DIR}")
    print(f"📄 TEMPLATE_PATH: {TEMPLATE_PATH}")
    print(f"📂 OUTPUT_DIR: {OUTPUT_DIR}")
    print(f"🔍 Template exists: {os.path.exists(TEMPLATE_PATH)}")
    
    # Invoice timestamps
    current_time = datetime.now()
    rounded_time = round_down_hour(current_time)

    invoice_date_str = rounded_time.strftime("%d/%m/%y")
    invoice_time_str = rounded_time.strftime("%H:%M")
    due_date = rounded_time + timedelta(days=7)
    due_date_str = due_date.strftime("%d/%m/%y")

    # Client data
    client_name = "John Doe"
    client_oib = "12345678901"
    client_address = "Testna 123"
    client_postal_code = "10000"
    client_city = "Zagreb"

    # Sample items - you can modify these
    sample_items_data = [
        {"name": "Web Design", "quantity": 1, "unit_price": 500.00},
        {"name": "Logo Design", "quantity": 1, "unit_price": 200.00},
        {"name": "Business Cards", "quantity": 100, "unit_price": 2.50}
    ]

    # Process items (same logic as in Flask app)
    items = []
    total = 0.0
    
    print("\n📊 PROCESSING ITEMS:")
    for i, item_data in enumerate(sample_items_data):
        try:
            quantity = item_data["quantity"]
            unit_price = item_data["unit_price"]
            line_total = quantity * unit_price
            total += line_total
            
            item = {
                "name": item_data["name"],
                "quantity": quantity,
                "unit_price": unit_price,
                "line_total": line_total,
                "formatted_unit_price": f"{unit_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", " "),
                "formatted_line_total": f"{line_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " "),
            }
            items.append(item)
            print(f"   ✅ {item['name']}: {quantity} x {unit_price} = {line_total}")
            
        except Exception as e:
            print(f"   ❌ Error processing item {i+1}: {e}")

    # Format total Croatian style
    formatted_total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
    print(f"\n💰 TOTAL: {formatted_total} EUR")

    # Year string (4 digits)
    year_str = rounded_time.strftime("%Y")

    # Calculate next invoice number for the year
    next_invoice_num = get_next_invoice_number(OUTPUT_DIR, year_str)

    # Invoice number string "X/2/2" where X is incrementing number
    invoice_number = f"{next_invoice_num}/2/2"

    # Prepare output directory and filename
    safe_client_name = client_name.replace(" ", "").replace("/", "_")
    year_folder = Path(OUTPUT_DIR) / year_str
    year_folder.mkdir(parents=True, exist_ok=True)

    pdf_filename = f"{next_invoice_num}-2-2_{safe_client_name}.pdf"
    final_pdf_path = year_folder / pdf_filename

    # Temp paths - use a temp directory in the output folder
    temp_dir = os.path.join(OUTPUT_DIR, 'temp_standalone')
    os.makedirs(temp_dir, exist_ok=True)
    temp_odt_path = os.path.join(temp_dir, 'temp_invoice.odt')
    temp_pdf_path = os.path.join(temp_dir, 'temp_invoice.pdf')

    # Compose combined date and time string
    invoice_date_time_str = f"{invoice_date_str} {invoice_time_str}"

    # Prepare context for template rendering (updated to match Flask app)
    context = {
        "client_name": client_name,
        "oib": client_oib,
        "address": client_address,
        "postal_code": client_postal_code,
        "city": client_city,
        "invoice_type": "obican",
        "invoice_number": invoice_number,
        "invoice_date": invoice_date_time_str,
        "invoice_time": invoice_time_str,
        "due_date": due_date_str,
        "due_date_desc": due_date_str,
        "location": "Rijeka",
        "items": items,  # This is the key change!
        "total": total,
        "formatted_total": formatted_total,
    }

    # Debug prints to verify
    print(f"\n📋 INVOICE DETAILS:")
    print(f"Invoice Number: {invoice_number}")
    print(f"Invoice Date/Time: {invoice_date_time_str}")
    print(f"Due Date: {due_date_str}")
    print(f"Client: {client_name}")
    print(f"Items: {len(items)}")
    print(f"Total: {formatted_total} EUR")

    print(f"\n🔧 TEMPLATE PROCESSING:")
    print(f"Template path: {TEMPLATE_PATH}")
    print(f"Template exists: {os.path.exists(TEMPLATE_PATH)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Year folder: {year_folder}")

    # Render the ODT invoice and convert to PDF
    if not render_odt_template(TEMPLATE_PATH, temp_odt_path, context):
        print("❌ Template rendering failed")
        exit(1)
    
    if not convert_to_pdf(temp_odt_path, temp_dir):
        print("❌ PDF conversion failed")
        exit(1)

    # Move the PDF to the final archive path
    if os.path.exists(temp_pdf_path):
        shutil.move(temp_pdf_path, final_pdf_path)
        print(f"✅ Invoice archived to: {final_pdf_path}")
    else:
        print(f"❌ PDF file not found: {temp_pdf_path}")
        exit(1)

    # Clean up the temporary directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print("🧹 Cleaned up temporary files")

    print("="*50)
    print("✅ INVOICE GENERATION COMPLETED SUCCESSFULLY")
    print("="*50 + "\n")