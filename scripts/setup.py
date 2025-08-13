from setuptools import setup

APP = ['scripts/gui_gnome.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': True,
    'packages': ['gi', 'jinja2'],
    'includes': [
        'gi',
        'gi.repository.Gtk',
        'gi.repository.Gdk',
        'gi.repository.GLib',
        'jinja2',
    ],
    'iconfile': 'static/icon.icns',  # Path to your .icns file
    'plist': {
        'LSUIElement': False,
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)