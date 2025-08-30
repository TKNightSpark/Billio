#!/bin/bash

# Complex installation script for macOS for the InvoiceProject application.
# - Checks and installs Homebrew (if needed)
# - Installs system dependencies required for PyGObject and GTK
# - Creates and activates Python virtual environment (venv)
# - Installs Python requirements from requirements.txt
# - Installs PyObjC for macOS-specific features
# - Runs the main GUI application

cd "$(dirname "$0")"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Welcome to the InvoiceProject installation script."

# Step 1: Install Homebrew if not installed
if ! command_exists brew; then
    echo "Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    # Add Homebrew to PATH for current session (Apple Silicon and Intel)
    eval "$(/opt/homebrew/bin/brew shellenv)" || true
    eval "$(/usr/local/bin/brew shellenv)" || true
else
    echo "Homebrew is already installed."
fi

# Step 2: Install required system packages via Homebrew
echo "Installing required system libraries (gtk+3, pygobject3, gobject-introspection, cairo, pkg-config)..."
brew install gtk+3 pygobject3 gobject-introspection cairo pkg-config

# Step 3: Create and activate virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

echo "Activating virtual environment..."
source venv/bin/activate

# Step 4: Install Python dependencies
echo "Installing Python packages from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# Step 5: Install PyObjC for macOS Dock icon support
echo "Installing PyObjC for macOS-specific functionality..."
pip install pyobjc

# Step 6: Run the GUI application
echo "Starting the gui_gnome.py application..."
python3 scripts/gui_gnome.py

echo "Script finished. Thank you for using InvoiceProject!"