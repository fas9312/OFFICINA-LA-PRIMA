import sqlite3
from pathlib import Path

import core

DEFAULT_DB_PATH = core.DATA_DIR / 'la_prima_01.db'
SELECTION_FILE = core.DATA_DIR / 'database_selection.txt'


def _read_configured_path():
    try:
        raw = SELECTION_FILE.read_text(encoding='utf-8').strip()
    except Exception:
        raw = ''
    return Path(raw).expanduser() if raw else None


def resolve_active_database():
    configured = _read_configured_path()
    if configured:
        try:
            candidate = configured.resolve()
        except Exception:
            candidate = configured
        if candidate.exists() and candidate.is_file():
            return candidate, ''
        return DEFAULT_DB_PATH, (
            f'Il database selezionato non è disponibile:\n{configured}\n\n'
            f'È stato aperto il database predefinito:\n{DEFAULT_DB_PATH}'
        )
    return DEFAULT_DB_PATH, ''


ACTIVE_DB_PATH, SELECTION_WARNING = resolve_active_database()
# Patch the core path before the rest of the application modules are imported.
core.DB_PATH = ACTIVE_DB_PATH


def validate_la_prima_database(path):
    """Validate an existing SQLite file without modifying it."""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, 'Il file selezionato non esiste.'
    try:
        uri = p.resolve().as_uri() + '?mode=ro'
        conn = sqlite3.connect(uri, uri=True)
        try:
            quick = conn.execute('PRAGMA quick_check').fetchone()
            if not quick or str(quick[0]).lower() != 'ok':
                return False, 'Il database SQLite risulta danneggiato o non integro.'
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            required = {'clients', 'vehicles', 'jobs', 'appointments', 'services', 'quotes', 'invoices', 'settings'}
            missing = sorted(required - tables)
            if missing:
                return False, 'Il file non sembra un database di LA PRIMA. Tabelle mancanti: ' + ', '.join(missing)
        finally:
            conn.close()
    except Exception as exc:
        return False, f'Impossibile aprire il database selezionato:\n{exc}'
    return True, ''


def configure_database(path):
    p = Path(path).expanduser().resolve()
    if p == DEFAULT_DB_PATH.resolve():
        clear_database_selection()
        return DEFAULT_DB_PATH
    SELECTION_FILE.write_text(str(p), encoding='utf-8')
    return p


def clear_database_selection():
    try:
        SELECTION_FILE.unlink()
    except FileNotFoundError:
        pass
    return DEFAULT_DB_PATH


def configured_database_path():
    return _read_configured_path()
