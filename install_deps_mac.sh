#!/bin/bash

# Kompleksna instalacijska skripta za macOS za InvoiceProject aplikaciju.
# - Proverava i instalira Homebrew (ako treba)
# - Instalira sistemske zavisnosti potrebne za PyGObject i GTK
# - Kreira i aktivira Python virtuelno okruženje (venv)
# - Instalira Python zahteve iz requirements.txt
# - Pokreće glavnu GUI aplikaciju

cd "$(dirname "$0")"

# Funkcija za provjeru postojanja komande
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Dobrodošli u instalacijsku skriptu za Billio aplikaciju."

# Korak 1: Instalacija Homebrew ako nije instaliran
if ! command_exists brew; then
    echo "Homebrew nije pronađen. Instaliram Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Dodavanje Homebrew u PATH za trenutnu sesiju (Apple Silicon i Intel)
    eval "$(/opt/homebrew/bin/brew shellenv)" || true
    eval "$(/usr/local/bin/brew shellenv)" || true
else
    echo "Homebrew je već instaliran."
fi

# Korak 2: Instalacija potrebnih sistema paketa putem Homebrew
echo "Instaliram potrebne sistemske biblioteke (gtk+3, pygobject3, gobject-introspection, cairo, pkg-config)..."
brew install gtk+3 pygobject3 gobject-introspection cairo pkg-config

# Korak 3: Kreiranje i aktivacija virtuelnog okruženja
if [ ! -d "venv" ]; then
    echo "Kreiranje virtuelnog okruženja 'venv'..."
    python3 -m venv venv
else
    echo "Virtuelno okruženje 'venv' već postoji."
fi

echo "Aktivacija virtuelnog okruženja..."
source venv/bin/activate

# Korak 4: Instalacija Python zavisnosti
echo "Instalacija Python paketa iz requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Korak 5: Pokretanje GUI aplikacije
echo "Pokretanje aplikacije gui_gnome.py..."
python3 scripts/gui_gnome.py

echo "Kraj skripte. Hvala što koristite InvoiceProject!"
"""

# Snimam kompletnu skriptu kao setup_full.sh unutar projekta
full_setup_path = os.path.join(extract_path_v2, 'InvoiceProject', 'setup_full.sh')
with open(full_setup_path, 'w', encoding='utf-8') as f:
    f.write(complete_setup_script)

# Podešavanje permisija
os.chmod(full_setup_path, 0o755)

full_setup_path

'/mnt/data/InvoiceProject_v2/InvoiceProject/setup_full.sh'