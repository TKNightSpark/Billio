#!/bin/bash

# Script to run gui_gnome.py from the 'scripts' folder

# Change current working directory to the project root

cd "$(dirname "$0")"

# Activate virtual environment if it exists

if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Python GUI application

python3 scripts/gui_gnome.py
billio_path = os.path.join(root_path, 'billio')

with open(billio_path, 'w', encoding='utf-8') as f:
    f.write(billio_script)

os.chmod(billio_path, 0o755)

billio_path
'/mnt/data/InvoiceProject_v2/InvoiceProject/billio'