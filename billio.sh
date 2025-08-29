#!/bin/bash



# Skipt za pokretanje gui_gnome.py iz 'scripts' foldera



# Promena trenutnog radnog direktorijuma na root projekta

cd "$(dirname "$0")"



# Aktivacija virtuelnog okruženja ako postoji

if [ -d "venv" ]; then

    source venv/bin/activate

fi



# Pokretanje Python GUI aplikacije

python3 scripts/gui_gnome.py

"""



billio_path = os.path.join(root_path, 'billio')

with open(billio_path, 'w', encoding='utf-8') as f:

    f.write(billio_script)



# Podešavanje da bude izvršna

os.chmod(billio_path, 0o755)



billio_path

'/mnt/data/InvoiceProject_v2/InvoiceProject/billio'
