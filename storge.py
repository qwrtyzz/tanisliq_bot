"""Safely choose persistent SQLite storage, optionally migrate local database."""
import logging
import os
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)


def prepare_database(destination: Path) -> None:
    destination = Path(destination)
    is_railway = bool(os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY_PROJECT_ID'))
    if is_railway and not str(destination).startswith('/data/'):
        log.warning('Database path %s is not on the recommended /data Railway volume', destination)
    if is_railway and str(destination).startswith('/data/') and not Path('/data').is_mount():
        raise RuntimeError('Railway volume is not mounted at /data. Refusing to write profiles to temporary storage.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    legacy = Path(__file__).with_name('tindraven.sqlite3')
    if destination.exists():
        log.info('Using existing SQLite database at %s', destination)
        return
    if legacy.exists() and legacy.resolve() != destination.resolve():
        # SQLite backup includes committed data and works with WAL-mode sources.
        # Never overwrite an existing destination.
        log.info('Migrating legacy SQLite database from %s to %s', legacy, destination)
        try:
            with sqlite3.connect(str(legacy)) as old:
                with sqlite3.connect(str(destination)) as new:
                    old.backup(new)
            log.info('Legacy SQLite database migration completed')
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    else:
        log.warning('No existing database found at %s. A new database will be created.', destination)
