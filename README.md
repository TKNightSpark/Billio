# Billio

Welcome to Billio, a GTK3-based Python application for creating invoices and exporting them to PDF.

---

## Clone the Repository (without Git)

If you don’t want to use Git, you can download only the `main` branch as a ZIP file:

1. Click the **Code** button on the repository page.
2. Select **Download ZIP**.
3. Extract the ZIP file on your machine.
4. You now have the `main` branch contents ready to use.

### Using Terminal

```bash
curl -L https://github.com/TKNightSpark/Billio/archive/refs/heads/main.zip -o Billio-main.zip
unzip Billio-main.zip
```

---

## Updating the Repository

### Using curl (without Git)

If you downloaded the repository as a ZIP using `curl`, you can update it by downloading the latest main branch and replacing the old files:

```bash
curl -L https://github.com/TKNightSpark/Billio/archive/refs/heads/main.zip -o Billio-main.zip
unzip -o Billio-main.zip
cp -r Billio-main/* /path/to/old/Billio/
rm -rf Billio-main Billio-main.zip
```

> ⚠️ Note: This replaces all files and will overwrite any local changes.

---

### Using Git (recommended)

If you cloned the repository using Git, updating is simpler:

```bash
cd Billio
git checkout main
git pull origin main
```

**Optional:** To fully sync with GitHub and overwrite local changes:

```bash
git fetch origin
git reset --hard origin/main
```

---

## macOS Installation Instructions

### 1. Prerequisites

This app requires the following dependencies installed on your Mac:

* **GTK3** (for the GUI)
* **LibreOffice** (for converting ODT to PDF)
* **Python 3** with `pyobjc` installed in the virtual environment (for proper macOS integration)

### 2. Install Dependencies

You have two options to install the dependencies:

---

### Option A: Manual Installation

#### Install Homebrew (if you don’t have it):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Install GTK3 via Homebrew:

```bash
brew install gtk+3
```

#### Install LibreOffice:

Download the latest macOS LibreOffice from [https://www.libreoffice.org/download/download/](https://www.libreoffice.org/download/download/)

**OR**

Install via Homebrew (may not be the latest version):

```bash
brew install libreoffice
```

Make sure LibreOffice is installed in `/Applications/LibreOffice.app` or the `soffice` CLI is available.

---

#### Set up your Python virtual environment:

Create and activate your Python virtual environment inside the project folder:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the required Python packages:

```bash
pip install -r requirements.txt
pip install pyobjc
```

---

### Option B: Automated Installation Script

You can use the provided `install_deps_mac.sh` script to automate Homebrew dependency installation and Python environment setup.

#### How to use:

Make sure the script is executable:

```bash
chmod +x install_deps_mac.sh
```

Run it:

```bash
./install_deps_mac.sh
```

This script will:

* Install Homebrew if needed,
* Install GTK3 and necessary system dependencies,
* Create and activate a Python virtual environment,
* Install the Python dependencies from `requirements.txt`,
* Install `pyobjc` automatically into the virtual environment,
* **Note:** LibreOffice installation is NOT automated due to its size — you must install it manually as described above.

---

### 3. Running the App

After dependencies are installed:

You can launch the app using the provided shell script `billio.sh` which will:

* Activate the Python virtual environment automatically,
* Run the `gui_gnome.py` script.

Make the launcher executable if needed:

```bash
chmod +x billio.sh
```

Run the launcher:

```bash
./billio.sh
```

Alternatively, if you have packaged the app with `py2app`, run the app bundle:

```bash
open dist/gui_gnome.app
```

---

### 4. Troubleshooting

* If the app fails to start due to GTK3 libraries not found, ensure your PATH includes Homebrew binaries:

```bash
export PATH="/usr/local/bin:$PATH"  # or /opt/homebrew/bin for Apple Silicon Macs
```

* If PDF generation fails, verify LibreOffice CLI works:

```bash
/Applications/LibreOffice.app/Contents/MacOS/soffice --version
```

---

### 5. Summary Table

| Dependency  | Install Command or Link                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------- |
| Homebrew    | `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"` |
| GTK3        | `brew install gtk+3`                                                                              |
| LibreOffice | Download from official site or `brew install libreoffice` (manual recommended)                    |
| Python venv | `python3 -m venv venv`                                                                            |
| Python pkgs | `pip install -r requirements.txt` and `pip install pyobjc`                                        |

---

### Python Dependencies

The project requires:

* `jinja2`
* `PyGObject` (available as the `gi` module)
* `pyobjc` (for macOS Dock icon and app integration)

Optional packages for macOS app packaging:

* `setuptools`
* `py2app`

Install the core requirements with:

```bash
pip install jinja2 PyGObject
pip install pyobjc
```

For packaging (optional):

```bash
pip install setuptools py2app
```

---

Thank you for using Billio! If you encounter any issues, please raise them in the project repository.
