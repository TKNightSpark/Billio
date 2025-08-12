import gi
import json
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from datetime import datetime, timedelta
from pathlib import Path
import subprocess, platform, os, shutil

from utilis import (
    round_down_hour, render_odt_template, convert_to_pdf,
    get_next_invoice_number, OUTPUT_DIR, TEMPLATE_PATH
)

def open_file_with_default_app(filepath):
    """Open file with default OS application."""
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.run(["open", filepath])
    else:
        subprocess.run(["xdg-open", filepath])


class InvoiceWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Kreiranje računa")
        self._configure_window()
        self._load_data()
        self._build_ui()
        self.populate_invoice_meta()
        self.populate_pdf_tree()

    def _configure_window(self):
        """Set window properties and main container."""
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)  # Dark theme preference
        self.set_default_size(900, 700)
        self.set_border_width(24)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(self.vbox)

    def _load_data(self):
        """Load naselja and ulice JSON data."""
        base_path = Path(__file__).resolve().parent.parent / "database"
        with open(base_path / "naselja.json", encoding="utf-8") as f:
            self.naselja = json.load(f)
        with open(base_path / "ulice.json", encoding="utf-8") as f:
            self.ulice = json.load(f)

    def _build_ui(self):
        """Build full UI."""
        self._build_invoice_meta_section()
        self._build_dates_section()
        self._build_client_and_items_section()
        self._build_generate_button()
        self._build_pdf_preview_section()

    def _build_invoice_meta_section(self):
        hbox = Gtk.Box(spacing=12, hexpand=True)
        self.vbox.pack_start(hbox, False, False, 0)

        hbox.pack_start(Gtk.Label(label="Vrsta računa", xalign=0), False, False, 0)
        self.invoice_type_combo = Gtk.ComboBoxText()
        for inv_type in ("obican", "r1"):
            self.invoice_type_combo.append_text(inv_type)
        self.invoice_type_combo.set_active(0)
        hbox.pack_start(self.invoice_type_combo, False, False, 0)

        hbox.pack_start(Gtk.Label(label="Broj računa (format: X/2/2)", xalign=0), False, False, 0)
        self.invoice_number_entry = Gtk.Entry()
        self.invoice_number_entry.set_editable(False)
        self.invoice_number_entry.set_width_chars(15)
        hbox.pack_start(self.invoice_number_entry, False, False, 0)

    def _build_dates_section(self):
        """Add date, time and due date entries."""
        def add_date_entry(container, label_text):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            container.pack_start(vbox, True, True, 0)
            vbox.pack_start(Gtk.Label(label=label_text, xalign=0), False, False, 0)
            entry = Gtk.Entry()
            entry.set_editable(False)
            vbox.pack_start(entry, False, False, 0)
            return entry

        hbox = Gtk.Box(spacing=12, hexpand=True)
        self.vbox.pack_start(hbox, False, False, 0)
        self.date_entry = add_date_entry(hbox, "Datum")
        self.time_entry = add_date_entry(hbox, "Vrijeme")
        self.due_entry = add_date_entry(hbox, "Rok plaćanja")

    def _build_client_and_items_section(self):
        """Build left (client info) and right (items) columns."""
        columns_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.vbox.pack_start(columns_hbox, True, True, 0)

        self._build_client_info(columns_hbox)
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        columns_hbox.pack_start(separator, False, False, 0)
        self._build_items_section(columns_hbox)

    def _build_client_info(self, parent_box):
        client_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        parent_box.pack_start(client_vbox, True, True, 0)

        client_label = Gtk.Label()
        client_label.set_markup("<span font='18' foreground='#5C6BC0'>Podaci o kupcu</span>")
        client_label.set_xalign(0)
        client_vbox.pack_start(client_label, False, False, 6)

        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        client_vbox.pack_start(grid, True, True, 0)

        # Fields: label text, col, row
        fields = [
            ("Naziv / Ime i prezime", 0, 0),
            ("OIB", 1, 0),
            ("Adresa", 0, 1),
            ("Poštanski broj", 0, 2),
            ("Grad", 1, 2),
        ]
        self.client_entries = {}

        for text, col, row in fields:
            label = Gtk.Label(label=text, xalign=0)
            grid.attach(label, col, row * 2, 1, 1)

            if text == "Grad":
                entry = self._create_city_entry()
            elif text == "Adresa":
                entry = self._create_street_entry()
            else:
                entry = Gtk.Entry()

            grid.attach(entry, col, row * 2 + 1, 1, 1)
            self.client_entries[text] = entry

        grid.set_column_homogeneous(False)
        grid.set_column_spacing(18)

    def _create_city_entry(self):
        entry = Gtk.Entry()
        completion = Gtk.EntryCompletion()
        completion.set_text_column(0)
        city_store = Gtk.ListStore(str)
        cities = sorted({n["NASELJE_NAZIV"] for n in self.naselja})
        for city in cities:
            city_store.append([city])
        completion.set_model(city_store)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)
        entry.set_completion(completion)
        entry.connect("changed", self.on_city_changed)
        return entry

    def _create_street_entry(self):
        entry = Gtk.Entry()
        completion = Gtk.EntryCompletion()
        completion.set_text_column(0)
        self.street_store = Gtk.ListStore(str)
        completion.set_model(self.street_store)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)
        entry.set_completion(completion)
        return entry

    def _build_items_section(self, parent_box):
        items_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        parent_box.pack_start(items_vbox, True, True, 0)

        items_label = Gtk.Label()
        items_label.set_markup("<span font='18' foreground='#5C6BC0'>Stavke</span>")
        items_label.set_xalign(0)
        items_vbox.pack_start(items_label, False, False, 6)

        self.items_listbox = Gtk.ListBox()
        self.items_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(147)
        scrolled.add(self.items_listbox)
        items_vbox.pack_start(scrolled, True, True, 0)

        add_item_box = Gtk.Box(spacing=10)
        items_vbox.pack_start(add_item_box, False, False, 0)

        self.new_item_name = Gtk.Entry()
        self.new_item_name.set_placeholder_text("Naziv stavke")
        self.new_item_qty = Gtk.Entry()
        self.new_item_qty.set_placeholder_text("Količina")
        self.new_item_price = Gtk.Entry()
        self.new_item_price.set_placeholder_text("Jedinična cijena")
        add_btn = Gtk.Button(label="Dodaj stavku")
        add_btn.connect("clicked", self.on_add_item)

        add_item_box.pack_start(self.new_item_name, True, True, 0)
        add_item_box.pack_start(self.new_item_qty, True, True, 0)
        add_item_box.pack_start(self.new_item_price, True, True, 0)
        add_item_box.pack_start(add_btn, False, False, 0)

        self.grand_total_label = Gtk.Label(label="Ukupno: 0,00 EUR", xalign=1)
        items_vbox.pack_start(self.grand_total_label, False, False, 4)

    def _build_generate_button(self):
        btn = Gtk.Button(label="Kreiraj račun")
        btn.get_style_context().add_class("suggested-action")
        btn.connect("clicked", self.on_generate_invoice)
        self.vbox.pack_start(btn, False, False, 12)

    def _build_pdf_preview_section(self):
        label = Gtk.Label()
        label.set_markup("<span font='18' foreground='#5C6BC0'>Svi generirani računi</span>")
        label.set_xalign(0)
        self.vbox.pack_start(label, False, False, 12)

        self.pdfs_store = Gtk.TreeStore(str, str)  # Display name, full path

        self.pdfs_treeview = Gtk.TreeView(model=self.pdfs_store)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Računi", renderer, text=0)
        self.pdfs_treeview.append_column(col)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_min_content_height(150)
        scrolled.add(self.pdfs_treeview)
        self.vbox.pack_start(scrolled, True, True, 0)

        preview_btn = Gtk.Button(label="Pregledaj odabrani PDF")
        preview_btn.get_style_context().add_class("suggested-action")
        preview_btn.connect("clicked", self.on_preview_pdf)
        self.vbox.pack_start(preview_btn, False, False, 6)

        edit_btn = Gtk.Button(label="Uredi odabrani račun")
        edit_btn.connect("clicked", self.on_edit_invoice)
        self.vbox.pack_start(edit_btn, False, False, 6)

    def on_city_changed(self, entry):
        city_name = entry.get_text().strip()
        self.street_store.clear()
        if not city_name:
            self.client_entries["Poštanski broj"].set_text("")
            return

        matched_naselja = [n for n in self.naselja if n["NASELJE_NAZIV"].strip().lower() == city_name.lower()]
        naselje_ids = {n["NASELJE_MBR"] for n in matched_naselja}
        matching_streets = sorted({u["ULICA_NAZIV"] for u in self.ulice if u["NASELJE_MBR"] in naselje_ids})
        for street in matching_streets:
            self.street_store.append([street])

        if matched_naselja:
            zip_code = matched_naselja[0].get("ZIP", "")
            self.client_entries["Poštanski broj"].set_text(str(zip_code))
        else:
            self.client_entries["Poštanski broj"].set_text("")

    def on_add_item(self, widget):
        name = self.new_item_name.get_text().strip()
        qty = self.new_item_qty.get_text().strip()
        price = self.new_item_price.get_text().strip()

        if not name or not qty or not price:
            self.show_error("Popunite sva polja stavke!")
            return

        try:
            float(qty.replace(",", "."))
            float(price.replace(",", "."))
        except ValueError:
            self.show_error("Neispravna količina ili cijena!")
            return

        self._add_item_row(name, qty, price)

        self.new_item_name.set_text("")
        self.new_item_qty.set_text("")
        self.new_item_price.set_text("")

    def _add_item_row(self, name, qty, price):
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(spacing=10)
        row.add(hbox)

        name_entry = Gtk.Entry()
        name_entry.set_text(name)
        name_entry.set_hexpand(True)
        hbox.pack_start(name_entry, True, True, 0)

        qty_entry = Gtk.Entry()
        qty_entry.set_text(qty)
        qty_entry.set_width_chars(10)
        hbox.pack_start(qty_entry, False, False, 0)

        price_entry = Gtk.Entry()
        price_entry.set_text(price)
        price_entry.set_width_chars(15)
        hbox.pack_start(price_entry, False, False, 0)

        line_total_label = Gtk.Label(label="0,00", xalign=1)
        line_total_label.set_width_chars(10)
        hbox.pack_start(line_total_label, False, False, 0)

        remove_btn = Gtk.Button(label="Remove")
        remove_btn.connect("clicked", lambda w: self.remove_item_row(row))
        hbox.pack_start(remove_btn, False, False, 0)

        def on_value_changed(*args):
            self.update_line_total(qty_entry, price_entry, line_total_label)
            self.update_grand_total()

        qty_entry.connect("changed", on_value_changed)
        price_entry.connect("changed", on_value_changed)

        self.items_listbox.add(row)
        self.items_listbox.show_all()

        self.update_line_total(qty_entry, price_entry, line_total_label)
        self.update_grand_total()

    def remove_item_row(self, row):
        self.items_listbox.remove(row)
        self.update_grand_total()

    def update_line_total(self, qty_entry, price_entry, total_label):
        try:
            q = float(qty_entry.get_text().replace(",", "."))
            p = float(price_entry.get_text().replace(",", "."))
            total = q * p
            formatted = self.format_currency(total)
            total_label.set_text(formatted)
        except Exception:
            total_label.set_text("0,00")

    def update_grand_total(self):
        total = 0.0
        for row in self.items_listbox.get_children():
            hbox = row.get_child()
            line_total_label = next((w for w in hbox.get_children() if isinstance(w, Gtk.Label)), None)
            if line_total_label:
                text = line_total_label.get_text()
                try:
                    val = float(text.replace(" ", "").replace(",", "."))
                    total += val
                except ValueError:
                    pass
        formatted_total = self.format_currency(total)
        self.grand_total_label.set_text(f"Ukupno: {formatted_total} EUR")

    @staticmethod
    def format_currency(amount):
        s = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
        return s

    def populate_invoice_meta(self):
        now = datetime.now()
        rounded = round_down_hour(now)
        year_str = rounded.strftime("%Y")
        inv_num = f"{get_next_invoice_number(OUTPUT_DIR, year_str)}/2/2"
        self.invoice_number_entry.set_text(inv_num)
        self.date_entry.set_text(rounded.strftime("%d.%m.%Y"))
        self.time_entry.set_text(rounded.strftime("%H:%M"))
        self.due_entry.set_text((rounded + timedelta(days=7)).strftime("%d.%m.%Y"))

    def on_generate_invoice(self, widget):
        data = self._collect_invoice_data()
        if not data:
            return  # Errors shown in method

        # Prepare paths and filenames
        year_folder = Path(OUTPUT_DIR) / data['invoice_date'].strftime("%Y")
        year_folder.mkdir(parents=True, exist_ok=True)

        safe_client_name = data["client_name"].replace(" ", "").replace("/", "_")
        pdf_filename = f"{data['invoice_number'].replace('/', '-')}_{safe_client_name}.pdf"
        final_pdf_path = year_folder / pdf_filename

        temp_dir = os.path.join(OUTPUT_DIR, "temp_gui")
        os.makedirs(temp_dir, exist_ok=True)
        temp_odt_path = os.path.join(temp_dir, "temp_invoice.odt")
        temp_pdf_path = os.path.join(temp_dir, "temp_invoice.pdf")

        context = data['context']

        try:
            if not render_odt_template(TEMPLATE_PATH, temp_odt_path, context):
                self.show_error("Neuspjelo kreiranje ODT predloška.")
                return

            if not convert_to_pdf(temp_odt_path, temp_dir):
                self.show_error("Neuspjelo konvertiranje PDF. Provjerite je li LibreOffice instaliran.")
                return

            if not os.path.exists(temp_pdf_path):
                self.show_error("PDF datoteka nije pronađena nakon konverzije.")
                return

            # Save ODT next to PDF
            final_odt_path = year_folder / pdf_filename.replace(".pdf", ".odt")
            shutil.copy(temp_odt_path, final_odt_path)

            # Save JSON data
            json_folder = Path(OUTPUT_DIR) / "._invoice_data" / year_folder.name
            json_folder.mkdir(parents=True, exist_ok=True)
            final_json_path = json_folder / pdf_filename.replace(".pdf", ".json")
            with open(final_json_path, "w", encoding="utf-8") as jf:
                json.dump(context, jf, ensure_ascii=False, indent=2)

            shutil.move(temp_pdf_path, final_pdf_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            dialog = Gtk.MessageDialog(parent=self,
                                       flags=0,
                                       message_type=Gtk.MessageType.INFO,
                                       buttons=Gtk.ButtonsType.OK,
                                       text=f"Račun uspješno kreiran:\n{final_pdf_path}")
            dialog.run()
            dialog.destroy()

            open_file_with_default_app(final_pdf_path)
            self.populate_pdf_tree()

        except Exception as e:
            self.show_error(f"Neočekivana greška: {e}")

    def _collect_invoice_data(self):
        """Collect and validate all invoice form data, return dict or None if errors."""
        client_name = self.client_entries["Naziv / Ime i prezime"].get_text().strip()
        if not client_name:
            self.show_error("Naziv kupca je obavezan.")
            return None

        oib = self.client_entries["OIB"].get_text().strip()
        address = self.client_entries["Adresa"].get_text().strip()
        postal_code = self.client_entries["Poštanski broj"].get_text().strip()
        city = self.client_entries["Grad"].get_text().strip()

        selected_type = self.invoice_type_combo.get_active_text()
        invoice_type = "R1" if selected_type.lower() == "r1" else ""
        invoice_number = self.invoice_number_entry.get_text()
        invoice_date_str = self.date_entry.get_text()
        invoice_time_str = self.time_entry.get_text()
        due_date_str = self.due_entry.get_text()

        # Parse date/time
        try:
            invoice_date = datetime.strptime(invoice_date_str, "%d.%m.%Y")
        except ValueError:
            invoice_date = datetime.now()

        try:
            invoice_time = datetime.strptime(invoice_time_str, "%H:%M").time()
        except ValueError:
            invoice_time = datetime.now().time()

        try:
            due_date = datetime.strptime(due_date_str, "%d.%m.%Y")
        except ValueError:
            due_date = invoice_date + timedelta(days=7)

        # Collect items
        items = []
        for row in self.items_listbox.get_children():
            hbox = row.get_child()
            entries = [w for w in hbox.get_children() if isinstance(w, Gtk.Entry)]
            if len(entries) != 3:
                continue

            name = entries[0].get_text().strip()
            if not name:
                continue
            qty_str = entries[1].get_text().strip()
            price_str = entries[2].get_text().strip()
            try:
                qty = float(qty_str.replace(",", "."))
                price = float(price_str.replace(",", "."))
                line_total = qty * price
                items.append({
                    "name": name,
                    "quantity": qty,
                    "unit_price": price,
                    "line_total": line_total,
                    "formatted_unit_price": self.format_currency(price),
                    "formatted_line_total": self.format_currency(line_total),
                })
            except ValueError:
                self.show_error(f"Pogrešan unos količine ili cijene za stavku: {name}")
                return None

        if not items:
            self.show_error("Morate unijeti barem jednu stavku za račun.")
            return None

        total = sum(i["line_total"] for i in items)

        context = {
            "client_name": client_name,
            "oib": oib,
            "address": address,
            "postal_code": postal_code,
            "city": city,
            "invoice_type": invoice_type,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.strftime("%d.%m.%Y") + " " + invoice_time.strftime("%H:%M"),
            "invoice_time": invoice_time.strftime("%H:%M"),
            "due_date": due_date.strftime("%d.%m.%Y"),
            "due_date_desc": due_date.strftime("%d.%m.%Y"),
            "location": "Rijeka",
            "items": items,
            "total": total,
            "formatted_total": self.format_currency(total),
        }

        return {
            "context": context,
            "invoice_date": invoice_date,
            "invoice_number": invoice_number,
            "client_name": client_name,
        }

    def populate_pdf_tree(self):
        self.pdfs_store.clear()
        base = Path(OUTPUT_DIR)
        if not base.exists():
            return

        for year_folder in sorted(base.iterdir()):
            if not year_folder.is_dir() or year_folder.name.startswith("._invoice_data"):
                continue

            year_iter = self.pdfs_store.append(None, [year_folder.name, str(year_folder)])
            for pdf_file in sorted(year_folder.glob("*.pdf")):
                self.pdfs_store.append(year_iter, [pdf_file.name, str(pdf_file)])

    def on_preview_pdf(self, widget):
        selection = self.pdfs_treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            self.show_error("Molimo odaberite PDF za pregled.")
            return
        path = Path(model[tree_iter][1])
        if path.is_dir():
            self.show_error("Molimo odaberite PDF, ne folder.")
            return
        if not path.exists():
            self.show_error("Datoteka ne postoji.")
            self.populate_pdf_tree()
            return
        open_file_with_default_app(str(path))

    def on_edit_invoice(self, widget):
        selection = self.pdfs_treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            self.show_error("Molimo odaberite račun za uređivanje.")
            return

        pdf_path = Path(model[tree_iter][1])
        if pdf_path.is_dir():
            self.show_error("Molimo odaberite PDF, ne folder.")
            return

        year_folder = pdf_path.parent.name
        json_path = Path(OUTPUT_DIR) / "._invoice_data" / year_folder / pdf_path.name.replace(".pdf", ".json")
        if not json_path.exists():
            self.show_error("Podaci za uređivanje nisu pronađeni.")
            return

        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                data = json.load(jf)

            # Populate form fields
            self.invoice_number_entry.set_text(data.get("invoice_number", ""))
            self.date_entry.set_text(data.get("invoice_date", "").split()[0])
            self.time_entry.set_text(data.get("invoice_time", ""))
            self.due_entry.set_text(data.get("due_date", ""))

            self.client_entries["Naziv / Ime i prezime"].set_text(data.get("client_name", ""))
            self.client_entries["OIB"].set_text(data.get("oib", ""))
            self.client_entries["Adresa"].set_text(data.get("address", ""))
            self.client_entries["Poštanski broj"].set_text(data.get("postal_code", ""))
            self.client_entries["Grad"].set_text(data.get("city", ""))

            # Clear current items
            for row in list(self.items_listbox.get_children()):
                self.items_listbox.remove(row)

            for item in data.get("items", []):
                self.new_item_name.set_text(item["name"])
                self.new_item_qty.set_text(str(item["quantity"]))
                self.new_item_price.set_text(str(item["unit_price"]))
                self.on_add_item(None)

        except Exception as e:
            self.show_error(f"Greška prilikom učitavanja: {e}")

    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = InvoiceWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()