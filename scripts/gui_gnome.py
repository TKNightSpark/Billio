import gi
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
    if platform.system() == "Windows":
        os.startfile(filepath)
    elif platform.system() == "Darwin":
        subprocess.run(["open", filepath])
    else:
        subprocess.run(["xdg-open", filepath])

class InvoiceWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Kreiranje računa")

        # Enable dark mode preference
        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)

        self.set_default_size(900, 700)
        self.set_border_width(24)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(self.vbox)

        # Title
        label = Gtk.Label()
        label.set_hexpand(True)
        label.set_justify(Gtk.Justification.CENTER)
        self.vbox.pack_start(label, False, False, 0)

        # Invoice meta (invoice type, number)
        hbox_meta = Gtk.Box(spacing=12, hexpand=True)
        self.vbox.pack_start(hbox_meta, False, False, 0)

        invoice_type_label = Gtk.Label(label="Vrsta računa", xalign=0)
        hbox_meta.pack_start(invoice_type_label, False, False, 0)

        self.invoice_type_combo = Gtk.ComboBoxText()
        self.invoice_type_combo.append_text("obican")
        self.invoice_type_combo.append_text("r1")
        self.invoice_type_combo.set_active(0)
        hbox_meta.pack_start(self.invoice_type_combo, False, False, 0)

        inv_number_label = Gtk.Label(label="Broj računa (format: X/2/2)", xalign=0)
        hbox_meta.pack_start(inv_number_label, False, False, 0)

        self.invoice_number_entry = Gtk.Entry()
        self.invoice_number_entry.set_editable(False)
        hbox_meta.pack_start(self.invoice_number_entry, False, False, 0)
        self.invoice_number_entry.set_width_chars(15)

        # Dates row (invoice date/time/due date)
        hbox_dates = Gtk.Box(spacing=12, hexpand=True)
        self.vbox.pack_start(hbox_dates, False, False, 0)

        def add_date_entry(box, label_text):
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.pack_start(vbox, True, True, 0)
            lbl = Gtk.Label(label=label_text, xalign=0)
            vbox.pack_start(lbl, False, False, 0)
            entry = Gtk.Entry()
            entry.set_editable(False)
            vbox.pack_start(entry, False, False, 0)
            return entry

        self.date_entry = add_date_entry(hbox_dates, "Datum")
        self.time_entry = add_date_entry(hbox_dates, "Vrijeme")
        self.due_entry = add_date_entry(hbox_dates, "Rok plaćanja")

        # Horizontal box for Client Info and Items side by side
        columns_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.vbox.pack_start(columns_hbox, True, True, 0)

        # Left column: Client info
        client_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        columns_hbox.pack_start(client_vbox, True, True, 0)

        client_label = Gtk.Label()
        client_label.set_markup("<span font='18' foreground='#5C6BC0'>Podaci o kupcu</span>")
        client_label.set_xalign(0)
        client_vbox.pack_start(client_label, False, False, 6)

        grid = Gtk.Grid(column_spacing=12, row_spacing=6)
        client_vbox.pack_start(grid, True, True, 0)

        client_fields = [
            ("Naziv / Ime i prezime", 0, 0),
            ("OIB", 1, 0),
            ("Adresa", 0, 1),
            ("Poštanski broj", 0, 2),
            ("Grad", 1, 2),
        ]
        self.client_entries = {}

        for text, col, row in client_fields:
            lbl = Gtk.Label(label=text, xalign=0)
            grid.attach(lbl, col, row*2, 1, 1)
            entry = Gtk.Entry()
            grid.attach(entry, col, row*2+1, 1, 1)
            self.client_entries[text] = entry

        grid.set_column_homogeneous(False)
        grid.set_column_spacing(18)

        # Vertical separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        columns_hbox.pack_start(separator, False, False, 0)

        # Right column: Invoice items
        items_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        columns_hbox.pack_start(items_vbox, True, True, 0)

        items_label = Gtk.Label()
        items_label.set_markup("<span font='18' foreground='#5C6BC0'>Stavke</span>")
        items_label.set_xalign(0)
        items_vbox.pack_start(items_label, False, False, 6)

        self.items_listbox = Gtk.ListBox()
        self.items_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        items_scrolled = Gtk.ScrolledWindow()
        items_scrolled.set_min_content_height(147)
        items_scrolled.add(self.items_listbox)
        items_vbox.pack_start(items_scrolled, True, True, 0)

        # Add item controls box
        add_item_box = Gtk.Box(spacing=10)
        items_vbox.pack_start(add_item_box, False, False, 0)
        self.new_item_name = Gtk.Entry()
        self.new_item_name.set_placeholder_text("Naziv stavke")
        self.new_item_qty = Gtk.Entry()
        self.new_item_qty.set_placeholder_text("Količina")
        self.new_item_price = Gtk.Entry()
        self.new_item_price.set_placeholder_text("Jedinična cijena")
        add_item_btn = Gtk.Button(label="Dodaj stavku")
        add_item_btn.connect("clicked", self.on_add_item)

        add_item_box.pack_start(self.new_item_name, True, True, 0)
        add_item_box.pack_start(self.new_item_qty, True, True, 0)
        add_item_box.pack_start(self.new_item_price, True, True, 0)
        add_item_box.pack_start(add_item_btn, False, False, 0)

        # Grand total label
        self.grand_total_label = Gtk.Label(label="Ukupno: 0,00 EUR", xalign=1)
        items_vbox.pack_start(self.grand_total_label, False, False, 4)

        # Generate invoice button under both columns
        generate_btn = Gtk.Button(label="Kreiraj račun")
        generate_btn.get_style_context().add_class("suggested-action")
        generate_btn.connect("clicked", self.on_generate_invoice)
        self.vbox.pack_start(generate_btn, False, False, 12)

        # PDF Preview section
        pdfs_label = Gtk.Label()
        pdfs_label.set_markup("<span font='18' foreground='#5C6BC0'>Svi generirani računi</span>")
        pdfs_label.set_xalign(0)
        self.vbox.pack_start(pdfs_label, False, False, 12)

        self.pdfs_store = Gtk.TreeStore(str, str)  # Display name, Full path

        self.pdfs_treeview = Gtk.TreeView(model=self.pdfs_store)
        renderer = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn("Računi", renderer, text=0)
        self.pdfs_treeview.append_column(col)

        pdfs_scrolled = Gtk.ScrolledWindow()
        pdfs_scrolled.set_min_content_height(150)
        pdfs_scrolled.add(self.pdfs_treeview)
        self.vbox.pack_start(pdfs_scrolled, True, True, 0)

        preview_btn = Gtk.Button(label="Pregledaj odabrani PDF")
        preview_btn.get_style_context().add_class("suggested-action")
        preview_btn.connect("clicked", self.on_preview_pdf)
        self.vbox.pack_start(preview_btn, False, False, 6)

        self.populate_invoice_meta()
        self.populate_pdf_tree()

    def populate_invoice_meta(self):
        now = datetime.now()
        rounded = round_down_hour(now)
        self.invoice_number_entry.set_text(f"{get_next_invoice_number(OUTPUT_DIR, rounded.strftime('%Y'))}/2/2")
        self.date_entry.set_text(rounded.strftime("%d.%m.%Y"))
        self.time_entry.set_text(rounded.strftime("%H:%M"))
        self.due_entry.set_text((rounded + timedelta(days=7)).strftime("%d.%m.%Y"))

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

        self.new_item_name.set_text("")
        self.new_item_qty.set_text("")
        self.new_item_price.set_text("")

    def remove_item_row(self, row):
        self.items_listbox.remove(row)
        self.update_grand_total()

    def update_line_total(self, qty_entry, price_entry, total_label):
        try:
            q = float(qty_entry.get_text().replace(",", "."))
            p = float(price_entry.get_text().replace(",", "."))
            total = q * p
            formatted = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
            total_label.set_text(formatted)
        except:
            total_label.set_text("0,00")

    def update_grand_total(self):
        total = 0.0
        for row in self.items_listbox.get_children():
            hbox = row.get_child()
            label = None
            for w in hbox.get_children():
                if isinstance(w, Gtk.Label):
                    label = w
                    break
            if label:
                text = label.get_text()
                try:
                    val = float(text.replace(" ", "").replace(",", "."))
                    total += val
                except ValueError:
                    pass
        formatted_total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
        self.grand_total_label.set_text(f"Ukupno: {formatted_total} EUR")

    def on_generate_invoice(self, widget):
        client_name = self.client_entries["Naziv / Ime i prezime"].get_text().strip()
        oib = self.client_entries["OIB"].get_text().strip()
        address = self.client_entries["Adresa"].get_text().strip()
        postal_code = self.client_entries["Poštanski broj"].get_text().strip()
        city = self.client_entries["Grad"].get_text().strip()

        if not client_name:
            self.show_error("Naziv kupca je obavezan.")
            return

        invoice_type = self.invoice_type_combo.get_active_text()
        invoice_number = self.invoice_number_entry.get_text()
        invoice_date = self.date_entry.get_text()
        invoice_time = self.time_entry.get_text()
        due_date = self.due_entry.get_text()

        try:
            inv_date_obj = datetime.strptime(invoice_date, "%d.%m.%Y")
        except:
            inv_date_obj = datetime.now()

        try:
            due_date_obj = datetime.strptime(due_date, "%d.%m.%Y")
        except:
            due_date_obj = datetime.now() + timedelta(days=7)

        try:
            inv_time_obj = datetime.strptime(invoice_time, "%H:%M").time()
        except:
            inv_time_obj = datetime.now().time()

        items = []
        for row in self.items_listbox.get_children():
            hbox = row.get_child()
            entries = [w for w in hbox.get_children() if isinstance(w, Gtk.Entry)]
            if len(entries) != 3:
                continue

            name = entries[0].get_text().strip()
            qty_str = entries[1].get_text().strip()
            price_str = entries[2].get_text().strip()
            if not name:
                continue
            try:
                quantity = float(qty_str.replace(",", "."))
                unit_price = float(price_str.replace(",", "."))
                line_total = quantity * unit_price

                formatted_unit_price = f"{unit_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")
                formatted_line_total = f"{line_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")

                items.append({
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "formatted_unit_price": formatted_unit_price,
                    "formatted_line_total": formatted_line_total,
                })
            except Exception:
                self.show_error(f"Pogrešan unos količine ili cijene za stavku: {name}")
                return

        if not items:
            self.show_error("Morate unijeti barem jednu stavku za račun.")
            return

        total = sum(i["line_total"] for i in items)
        formatted_total = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", " ")

        year_str = inv_date_obj.strftime("%Y")
        year_folder = Path(OUTPUT_DIR) / year_str
        year_folder.mkdir(parents=True, exist_ok=True)

        safe_client_name = client_name.replace(" ", "").replace("/", "_")
        pdf_filename = f"{invoice_number.replace('/', '-')}_{safe_client_name}.pdf"
        final_pdf_path = year_folder / pdf_filename

        temp_dir = os.path.join(OUTPUT_DIR, "temp_gui")
        os.makedirs(temp_dir, exist_ok=True)
        temp_odt_path = os.path.join(temp_dir, "temp_invoice.odt")
        temp_pdf_path = os.path.join(temp_dir, "temp_invoice.pdf")

        invoice_date_display = inv_date_obj.strftime("%d.%m.%Y") + " " + inv_time_obj.strftime("%H:%M")
        due_date_display = due_date_obj.strftime("%d.%m.%Y")

        context = {
            "client_name": client_name,
            "oib": oib,
            "address": address,
            "postal_code": postal_code,
            "city": city,
            "invoice_type": invoice_type,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date_display,
            "invoice_time": inv_time_obj.strftime("%H:%M"),
            "due_date": due_date_display,
            "due_date_desc": due_date_display,
            "location": "Rijeka",
            "items": items,
            "total": total,
            "formatted_total": formatted_total,
        }

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

    def populate_pdf_tree(self):
        self.pdfs_store.clear()
        base = Path(OUTPUT_DIR)
        if not base.exists():
            return

        for year_folder in sorted(base.iterdir()):
            if year_folder.is_dir():
                year_iter = self.pdfs_store.append(None, [year_folder.name, str(year_folder)])
                for pdf_file in sorted(year_folder.glob("*.pdf")):
                    self.pdfs_store.append(year_iter, [pdf_file.name, str(pdf_file)])

    def on_preview_pdf(self, widget):
        selection = self.pdfs_treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.OK, text="Molimo odaberite PDF za pregled.")
            dialog.run()
            dialog.destroy()
            return

        path = model[tree_iter][1]
        p = Path(path)
        if p.is_dir():
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.OK, text="Molimo odaberite PDF, ne folder.")
            dialog.run()
            dialog.destroy()
            return

        if not p.exists():
            dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                       buttons=Gtk.ButtonsType.OK, text="Datoteka ne postoji.")
            dialog.run()
            dialog.destroy()
            self.populate_pdf_tree()
            return

        open_file_with_default_app(path)

    def show_error(self, message):
        dialog = Gtk.MessageDialog(parent=self, flags=0, message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK, text=message)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = InvoiceWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()