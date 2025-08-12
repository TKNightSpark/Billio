import gi
import json
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
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

def open_folder_in_file_manager(folder_path):
    """Open the specified folder in the system's default file manager"""
    if platform.system() == "Windows":
        os.startfile(folder_path)
    elif platform.system() == "Darwin":
        subprocess.run(["open", folder_path])
    else:
        subprocess.run(["xdg-open", folder_path])

class InvoiceWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Kreiranje računa")

        settings = Gtk.Settings.get_default()
        settings.set_property("gtk-application-prefer-dark-theme", True)

        self.set_default_size(900, 650)
        self.set_border_width(0)  # Remove default border for cleaner look

        # Apply custom CSS styling
        self._apply_custom_css()

        # Main container with padding
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_container.set_margin_left(16)
        main_container.set_margin_right(16)
        main_container.set_margin_top(16)
        main_container.set_margin_bottom(16)
        self.add(main_container)

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_container.pack_start(self.vbox, True, True, 0)

        # Load master data
        self._load_naselja_and_ulice()
        self._load_clients()

        self._build_ui()
        self.populate_invoice_meta()

    def _apply_custom_css(self):
        """Apply custom CSS styling for modern look"""
        css_provider = Gtk.CssProvider()
        css = """
        /* Card-like containers */
        .invoice-card {
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px;
            margin: 4px 0;
        }
        
        /* Section headers */
        .section-header {
            font-size: 16px;
            font-weight: 600;
            color: #64B5F6;
            margin-bottom: 8px;
        }
        
        /* Primary buttons */
        .btn-primary {
            background: linear-gradient(135deg, #42A5F5, #1E88E5);
            border: none;
            border-radius: 6px;
            color: white;
            font-weight: 600;
            padding: 8px 16px;
            margin: 2px;
            min-height: 36px;
        }
        
        .btn-primary:hover {
            background: linear-gradient(135deg, #1E88E5, #1565C0);
            box-shadow: 0 2px 8px rgba(66, 165, 245, 0.3);
        }
        
        /* Secondary buttons */
        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 6px;
            color: #E3F2FD;
            font-weight: 500;
            padding: 6px 12px;
            margin: 2px;
            min-height: 32px;
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.3);
        }
        
        /* Danger buttons */
        .btn-danger {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.4);
            border-radius: 4px;
            color: #FF8A80;
            padding: 4px 8px;
            font-size: 11px;
        }
        
        .btn-danger:hover {
            background: rgba(244, 67, 54, 0.3);
            color: #FFCDD2;
        }
        
        /* Modern entries */
        .modern-entry {
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(255, 255, 255, 0.05);
            padding: 6px 8px;
            min-height: 28px;
        }
        
        .modern-entry:focus {
            border-color: #42A5F5;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 0 1px rgba(66, 165, 245, 0.2);
        }
        
        /* Labels */
        .field-label {
            color: #B0BEC5;
            font-weight: 500;
            font-size: 12px;
            margin-bottom: 4px;
        }
        
        /* List items */
        .item-row {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 6px;
            margin: 2px 0;
            padding: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        /* Total display */
        .total-display {
            font-size: 16px;
            font-weight: 700;
            color: #4CAF50;
            padding: 8px;
            background: rgba(76, 175, 80, 0.1);
            border-radius: 6px;
            border-left: 3px solid #4CAF50;
        }
        
        /* Scrolled windows */
        .items-scroll {
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(0, 0, 0, 0.2);
        }
        """
        
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _load_naselja_and_ulice(self):
        base_path = Path(__file__).resolve().parent.parent / "database"
        with open(base_path / "naselja.json", encoding="utf-8") as f:
            self.naselja = json.load(f)
        with open(base_path / "ulice.json", encoding="utf-8") as f:
            self.ulice = json.load(f)

    def _load_clients(self):
        clients_path = Path(__file__).resolve().parent.parent / "database" / "klijenti.json"
        if clients_path.exists():
            with open(clients_path, encoding="utf-8") as f:
                self.clients = json.load(f)
        else:
            self.clients = []

        self.client_name_store = Gtk.ListStore(str)
        self.client_name_store.clear()
        for client in self.clients:
            self.client_name_store.append([client['client_name']])

    def _save_clients(self):
        clients_path = Path(__file__).resolve().parent.parent / "database" / "klijenti.json"
        with open(clients_path, "w", encoding="utf-8") as f:
            json.dump(self.clients, f, ensure_ascii=False, indent=2)

    def _create_card_container(self, title=None, icon_name=None):
        """Create a card-like container with optional title and GNOME icon"""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("invoice-card")
        
        if title:
            header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            icon = None
            if icon_name:
                try:
                    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU)
                except Exception:
                    icon = None
            if icon:
                header_box.pack_start(icon, False, False, 0)
            title_label = Gtk.Label(label=title, xalign=0)
            title_label.get_style_context().add_class("section-header")
            header_box.pack_start(title_label, False, False, 0)
            card.pack_start(header_box, False, False, 0)
        
        return card

    def _create_styled_button(self, label, style_class="btn-secondary", icon_name=None):
        """Create a styled button with optional icon"""
        if icon_name:
            button = Gtk.Button()
            box = Gtk.Box(spacing=8)
            
            # Try to create icon, fallback to text if icon not available
            try:
                icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
                box.pack_start(icon, False, False, 0)
            except:
                pass  # Icon not available, just use text
                
            label_widget = Gtk.Label(label=label)
            box.pack_start(label_widget, False, False, 0)
            button.add(box)
        else:
            button = Gtk.Button(label=label)
        
        button.get_style_context().add_class(style_class)
        return button

    def _create_field_with_label(self, parent, label_text, entry_widget=None):
        """Create a field with styled label"""
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        label = Gtk.Label(label=label_text, xalign=0)
        label.get_style_context().add_class("field-label")
        vbox.pack_start(label, False, False, 0)
        
        if entry_widget is None:
            entry_widget = Gtk.Entry()
            entry_widget.get_style_context().add_class("modern-entry")
        
        vbox.pack_start(entry_widget, False, False, 0)
        parent.pack_start(vbox, True, True, 0)
        
        return entry_widget

    def _build_ui(self):
        self._build_invoice_meta_section()
        self._build_client_and_items_section()
        self._build_action_buttons()

        # Setup client name completion AFTER client_entries dict initialized
        client_name_entry = self.client_entries.get("Naziv / Ime i prezime")
        if client_name_entry:
            completion = Gtk.EntryCompletion()
            completion.set_model(self.client_name_store)
            completion.set_text_column(0)
            completion.set_inline_completion(True)
            completion.set_popup_completion(True)
            client_name_entry.set_completion(completion)
            client_name_entry.connect("changed", self.on_client_name_changed)

    def _build_invoice_meta_section(self):
        """Build merged invoice meta and dates section with card styling"""
        card = self._create_card_container("Osnovni podaci računa", icon_name="emblem-system-symbolic")
        self.vbox.pack_start(card, False, False, 0)

        hbox_top = Gtk.Box(spacing=16, hexpand=True)
        card.pack_start(hbox_top, False, False, 0)

        # Invoice type
        type_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        type_label = Gtk.Label(label="Vrsta računa", xalign=0)
        type_label.get_style_context().add_class("field-label")
        type_vbox.pack_start(type_label, False, False, 0)
        
        self.invoice_type_combo = Gtk.ComboBoxText()
        self.invoice_type_combo.get_style_context().add_class("modern-entry")
        self.invoice_type_combo.append_text("Običan račun")
        self.invoice_type_combo.append_text("R1")
        self.invoice_type_combo.set_active(0)
        type_vbox.pack_start(self.invoice_type_combo, False, False, 0)
        hbox_top.pack_start(type_vbox, False, False, 0)

        # Invoice number
        self.invoice_number_entry = self._create_field_with_label(hbox_top, "Broj računa")
        self.invoice_number_entry.set_width_chars(15)

        hbox_bottom = Gtk.Box(spacing=16, hexpand=True)
        card.pack_start(hbox_bottom, False, False, 0)

        self.date_entry = self._create_field_with_label(hbox_bottom, "Datum")
        self.time_entry = self._create_field_with_label(hbox_bottom, "Vrijeme")
        self.due_entry = self._create_field_with_label(hbox_bottom, "Rok plaćanja")

    def _build_client_and_items_section(self):
        """Build client and items sections with improved layout"""
        columns_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.vbox.pack_start(columns_hbox, True, True, 0)

        self._build_client_info(columns_hbox)
        self._build_items_section(columns_hbox)

    def _build_client_info(self, parent_box):
        """Build client info section with card styling"""
        client_card = self._create_card_container("Podaci o kupcu", icon_name="avatar-default-symbolic")
        parent_box.pack_start(client_card, True, True, 0)

        # Clear button with icon
        clear_btn = self._create_styled_button("Očisti polja", "btn-secondary", "edit-clear")
        clear_btn.set_tooltip_text("Očisti sva polja kupca")
        clear_btn.connect("clicked", self.on_clear_client_fields)
        client_card.pack_start(clear_btn, False, False, 0)

        # Grid for client fields
        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        client_card.pack_start(grid, True, True, 0)

        client_fields = {
            "Grad": {"type": "city"},
            "Poštanski broj": {},
            "Adresa": {"type": "street"},
            "Naziv / Ime i prezime": {},
            "OIB": {},
        }
        self.client_entries = {}

        for i, (label_text, props) in enumerate(client_fields.items()):
            col = 0 if i < 3 else 1
            row = i if col == 0 else i - 3
            
            # Create field container
            field_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            grid.attach(field_vbox, col, row, 1, 1)
            
            # Create label
            label = Gtk.Label(label=label_text, xalign=0)
            label.get_style_context().add_class("field-label")
            field_vbox.pack_start(label, False, False, 0)

            # Create entry
            if props.get("type") == "city":
                entry = self._create_city_entry()
            elif props.get("type") == "street":
                entry = self._create_street_entry()
            else:
                entry = Gtk.Entry()
                entry.get_style_context().add_class("modern-entry")

            field_vbox.pack_start(entry, False, False, 0)
            self.client_entries[label_text] = entry

        grid.set_column_homogeneous(True)

    def _create_city_entry(self):
        entry = Gtk.Entry()
        entry.get_style_context().add_class("modern-entry")
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
        entry.get_style_context().add_class("modern-entry")
        completion = Gtk.EntryCompletion()
        completion.set_text_column(0)
        self.street_store = Gtk.ListStore(str)
        completion.set_model(self.street_store)
        completion.set_inline_completion(True)
        completion.set_popup_completion(True)
        entry.set_completion(completion)
        return entry

    def _build_items_section(self, parent_box):
        """Build items section with modern styling"""
        items_card = self._create_card_container("Stavke računa", icon_name="text-x-generic-symbolic")
        parent_box.pack_start(items_card, True, True, 0)

        # Items list with styled scrolled window
        self.items_listbox = Gtk.ListBox()
        self.items_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.get_style_context().add_class("items-scroll")
        scrolled.set_min_content_height(140)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.items_listbox)
        items_card.pack_start(scrolled, True, True, 0)

        # Add item section
        add_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        items_card.pack_start(add_section, False, False, 0)

        # Add item fields in a grid
        add_grid = Gtk.Grid(column_spacing=6, row_spacing=4)
        add_section.pack_start(add_grid, False, False, 0)

        # Create styled entries for adding items
        name_label = Gtk.Label(label="Naziv stavke", xalign=0)
        name_label.get_style_context().add_class("field-label")
        add_grid.attach(name_label, 0, 0, 1, 1)
        
        self.new_item_name = Gtk.Entry()
        self.new_item_name.get_style_context().add_class("modern-entry")
        self.new_item_name.set_placeholder_text("Unesite naziv...")
        add_grid.attach(self.new_item_name, 0, 1, 1, 1)

        qty_label = Gtk.Label(label="Količina", xalign=0)
        qty_label.get_style_context().add_class("field-label")
        add_grid.attach(qty_label, 1, 0, 1, 1)
        
        self.new_item_qty = Gtk.Entry()
        self.new_item_qty.get_style_context().add_class("modern-entry")
        self.new_item_qty.set_placeholder_text("1,00")
        self.new_item_qty.set_width_chars(8)
        add_grid.attach(self.new_item_qty, 1, 1, 1, 1)

        price_label = Gtk.Label(label="Jedinična cijena", xalign=0)
        price_label.get_style_context().add_class("field-label")
        add_grid.attach(price_label, 2, 0, 1, 1)
        
        self.new_item_price = Gtk.Entry()
        self.new_item_price.get_style_context().add_class("modern-entry")
        self.new_item_price.set_placeholder_text("0,00")
        self.new_item_price.set_width_chars(12)
        add_grid.attach(self.new_item_price, 2, 1, 1, 1)

        # Add button with icon
        add_btn = self._create_styled_button("Dodaj stavku", "btn-primary", "list-add")
        add_btn.connect("clicked", self.on_add_item)
        add_grid.attach(add_btn, 3, 1, 1, 1)

        # Total display with modern styling
        self.grand_total_label = Gtk.Label(label="Ukupno: 0,00 EUR", xalign=1)
        self.grand_total_label.get_style_context().add_class("total-display")
        items_card.pack_start(self.grand_total_label, False, False, 0)

    def _build_action_buttons(self):
        """Build action buttons section with improved styling"""
        actions_card = self._create_card_container()
        self.vbox.pack_start(actions_card, False, False, 0)

        # Button container
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_halign(Gtk.Align.CENTER)
        actions_card.pack_start(button_box, False, False, 0)

        # Generate invoice button (primary)
        generate_btn = self._create_styled_button(" Kreiraj račun", "btn-primary", "document-new")
        generate_btn.connect("clicked", self.on_generate_invoice)
        button_box.pack_start(generate_btn, False, False, 0)

        # Edit existing invoice button
        edit_btn = self._create_styled_button("Učitaj postojeći račun", "btn-secondary", "document-open")
        edit_btn.set_tooltip_text("Odaberi PDF račun za uređivanje")
        edit_btn.connect("clicked", self.on_select_invoice_for_editing)
        button_box.pack_start(edit_btn, False, False, 0)

    # ------------------ Callback handlers ---------------------

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

    def on_client_name_changed(self, entry):
        name = entry.get_text().strip()
        client = self._find_client_by_name(name)
        if client:
            self._fill_client_fields(client)

    def _find_client_by_name(self, name):
        for client in self.clients:
            if client["client_name"].strip().lower() == name.lower():
                return client
        return None

    def _fill_client_fields(self, client):
        self.client_entries["OIB"].set_text(client.get("oib", ""))
        self.client_entries["Adresa"].set_text(client.get("address", ""))
        self.client_entries["Poštanski broj"].set_text(client.get("postal_code", ""))
        self.client_entries["Grad"].set_text(client.get("city", ""))

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
        """Create styled item row"""
        row = Gtk.ListBoxRow()
        row.get_style_context().add_class("item-row")
        
        hbox = Gtk.Box(spacing=8, margin=6)
        row.add(hbox)

        # Name entry
        name_entry = Gtk.Entry()
        name_entry.get_style_context().add_class("modern-entry")
        name_entry.set_text(name)
        name_entry.set_hexpand(True)
        hbox.pack_start(name_entry, True, True, 0)

        # Quantity entry
        qty_entry = Gtk.Entry()
        qty_entry.get_style_context().add_class("modern-entry")
        qty_entry.set_text(qty)
        qty_entry.set_width_chars(8)
        hbox.pack_start(qty_entry, False, False, 0)

        # Price entry
        price_entry = Gtk.Entry()
        price_entry.get_style_context().add_class("modern-entry")
        price_entry.set_text(price)
        price_entry.set_width_chars(12)
        hbox.pack_start(price_entry, False, False, 0)

        # Line total label
        line_total_label = Gtk.Label(label="0,00", xalign=1)
        line_total_label.set_width_chars(10)
        line_total_label.get_style_context().add_class("field-label")
        hbox.pack_start(line_total_label, False, False, 0)

        # Remove button with modern styling
        remove_btn = self._create_styled_button("✕", "btn-danger")
        remove_btn.set_tooltip_text("Ukloni stavku")
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
        except:
            total_label.set_text("0,00")

    def update_grand_total(self):
        total = 0.0
        for row in self.items_listbox.get_children():
            hbox = row.get_child()
            labels = [w for w in hbox.get_children() if isinstance(w, Gtk.Label)]
            if labels:
                # Find the total label (should be the one with currency format)
                for label in labels:
                    text = label.get_text()
                    if "," in text and text.replace(" ", "").replace(",", ".").replace(".", "").isdigit():
                        try:
                            val = float(text.replace(" ", "").replace(",", "."))
                            total += val
                            break
                        except ValueError:
                            continue
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

    def on_clear_client_fields(self, widget):
        fields_to_clear = [
            "Naziv / Ime i prezime",
            "Poštanski broj",
            "OIB",
            "Grad",
            "Adresa",
        ]
        for field in fields_to_clear:
            entry = self.client_entries.get(field)
            if entry:
                entry.set_text("")

    def on_generate_invoice(self, widget):
        data = self._collect_invoice_data()
        if not data:
            return  # Validation errors shown

        # Prompt to save client if new
        self._prompt_save_client(data['context'])

        year_folder = Path(OUTPUT_DIR) / data['invoice_date'].strftime("%Y")
        year_folder.mkdir(parents=True, exist_ok=True)

        # Format invoice number: replace '/' with '-'
        invoice_num_for_file = data['invoice_number'].replace('/', '-')

        # Lowercase client name and keep spaces intact
        client_name_for_file = data["client_name"].lower()

        # Build filename with ' - ' separator
        pdf_filename = f"{invoice_num_for_file} - {client_name_for_file}.pdf"
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

            final_odt_path = year_folder / pdf_filename.replace(".pdf", ".odt")
            shutil.copy(temp_odt_path, final_odt_path)

            json_folder = Path(OUTPUT_DIR) / "._invoice_data" / year_folder.name
            json_folder.mkdir(parents=True, exist_ok=True)
            final_json_path = json_folder / pdf_filename.replace(".pdf", ".json")
            with open(final_json_path, "w", encoding="utf-8") as jf:
                json.dump(context, jf, ensure_ascii=False, indent=2)

            shutil.move(temp_pdf_path, final_pdf_path)
            shutil.rmtree(temp_dir, ignore_errors=True)

            # Show success dialog with modern styling
            self.show_success(f"Račun uspješno kreiran:\n{final_pdf_path.name}")

            open_file_with_default_app(str(final_pdf_path))

        except Exception as e:
            self.show_error(f"Neočekivana greška: {e}")

    def _collect_invoice_data(self):
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

        try:
            invoice_date = datetime.strptime(invoice_date_str, "%d.%m.%Y")
        except:
            invoice_date = datetime.now()

        try:
            invoice_time = datetime.strptime(invoice_time_str, "%H:%M").time()
        except:
            invoice_time = datetime.now().time()

        try:
            due_date = datetime.strptime(due_date_str, "%d.%m.%Y")
        except:
            due_date = invoice_date + timedelta(days=7)

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

    def _prompt_save_client(self, context):
        if self._find_client_by_name(context["client_name"]):
            return  # Already saved

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.NONE,
            text="Želite li spremiti ovog kupca za buduću upotrebu?"
        )
        dialog.add_button("Ne", Gtk.ResponseType.NO)
        dialog.add_button("Da", Gtk.ResponseType.YES)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.clients.append({
                "client_name": context["client_name"],
                "oib": context["oib"],
                "address": context["address"],
                "postal_code": context["postal_code"],
                "city": context["city"],
            })
            self._save_clients()
            self.client_name_store.append([context["client_name"]])

    def on_select_invoice_for_editing(self, widget):
        """Open file dialog to select an invoice PDF for editing"""
        dialog = Gtk.FileChooserDialog(
            title="Odaberite račun za uređivanje",
            parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK
        )
        
        # Set default folder to OUTPUT_DIR
        output_path = Path(OUTPUT_DIR)
        if output_path.exists():
            dialog.set_current_folder(str(output_path))
        
        # Add filter for PDF files
        filter_pdf = Gtk.FileFilter()
        filter_pdf.set_name("PDF računi")
        filter_pdf.add_pattern("*.pdf")
        dialog.add_filter(filter_pdf)
        
        response = dialog.run()
        
        if response == Gtk.ResponseType.OK:
            pdf_path = Path(dialog.get_filename())
            self._load_invoice_for_editing(pdf_path)
        
        dialog.destroy()

    def _load_invoice_for_editing(self, pdf_path):
        """Load invoice data from JSON and populate the form"""
        if not pdf_path.exists():
            self.show_error("Datoteka ne postoji.")
            return

        # Find corresponding JSON file
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

            # Set invoice type
            if data.get("invoice_type", "") == "R1":
                self.invoice_type_combo.set_active(1)  # r1
            else:
                self.invoice_type_combo.set_active(0)  # obican

            # Populate client fields
            self.client_entries["Naziv / Ime i prezime"].set_text(data.get("client_name", ""))
            self.client_entries["OIB"].set_text(data.get("oib", ""))
            self.client_entries["Adresa"].set_text(data.get("address", ""))
            self.client_entries["Poštanski broj"].set_text(data.get("postal_code", ""))
            self.client_entries["Grad"].set_text(data.get("city", ""))

            # Clear existing items
            for row in list(self.items_listbox.get_children()):
                self.items_listbox.remove(row)

            # Populate items
            for item in data.get("items", []):
                self._add_item_row(
                    item["name"], 
                    str(item["quantity"]).replace(".", ","),  # Convert back to Croatian format
                    str(item["unit_price"]).replace(".", ",")  # Convert back to Croatian format
                )

            self.show_info(f"Učitan račun: {pdf_path.name}")

        except Exception as e:
            self.show_error(f"Greška prilikom učitavanja: {e}")

    def show_error(self, message):
        """Show error dialog with modern styling"""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Greška"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_success(self, message):
        """Show success dialog with modern styling"""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Uspjeh"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_info(self, message):
        """Show info dialog with modern styling"""
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Informacija"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


if __name__ == "__main__":
    win = InvoiceWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()