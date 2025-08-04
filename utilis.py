import os
import zipfile
import shutil
import subprocess
from jinja2 import Template
from pathlib import Path

def round_down_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

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
        if not os.path.exists(odt_path):
            raise FileNotFoundError(f"ODT file not found: {odt_path}")

        subprocess.run(['soffice', '--version'], capture_output=True, check=True)

        result = subprocess.run([
            'soffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', output_dir,
            odt_path
        ], capture_output=True, text=True, timeout=30)

        print(f"LibreOffice exit code: {result.returncode}")
        if result.stdout:
            print(f"stdout: {result.stdout}")
        if result.stderr:
            print(f"stderr: {result.stderr}")

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
    year_folder = Path(output_dir) / year_str
    if not year_folder.exists():
        return 1
    pdf_files = list(year_folder.glob("*-2-2_*.pdf"))
    return len(pdf_files) + 1