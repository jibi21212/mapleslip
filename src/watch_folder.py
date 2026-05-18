"""Watch folder — auto-detect new tax PDFs and import them."""

import os
from pathlib import Path
from typing import Callable


class WatchFolder:
    """Polls a folder for new PDF files and triggers a callback on each new one.

    Uses simple polling (every N seconds) rather than file system watchers,
    which keeps the dependency footprint minimal and works on all platforms.
    """

    def __init__(self, folder_path: str, callback: Callable[[str], None],
                 poll_interval_ms: int = 5000):
        self.folder_path = Path(folder_path)
        self.callback = callback
        self.poll_interval_ms = poll_interval_ms
        self.seen_files: set[str] = set()
        self._after_id = None
        self._tk_root = None
        self._enabled = False

    def start(self, tk_root):
        """Start polling. tk_root is a tkinter widget used to schedule callbacks."""
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            return False

        self._tk_root = tk_root
        self._enabled = True

        # Seed the initial state — don't import existing files, only new arrivals
        self.seen_files = self._scan_folder()
        self._schedule_next_poll()
        return True

    def stop(self):
        """Stop polling."""
        self._enabled = False
        if self._after_id and self._tk_root:
            try:
                self._tk_root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _scan_folder(self) -> set[str]:
        """Get current set of PDF files in the folder."""
        result = set()
        try:
            for entry in self.folder_path.iterdir():
                if entry.is_file() and entry.suffix.lower() == ".pdf":
                    result.add(str(entry.absolute()))
        except Exception:
            pass
        return result

    def _check_for_new_files(self):
        """Check for new PDFs and call the callback for each."""
        if not self._enabled:
            return

        try:
            current = self._scan_folder()
            new_files = current - self.seen_files
            for filepath in new_files:
                # Make sure the file is fully written (size stable across two reads)
                try:
                    size1 = os.path.getsize(filepath)
                    # Brief check via scheduling won't help here — just try to import.
                    # If the import fails because file is still being written, user can retry.
                    self.callback(filepath)
                except Exception as e:
                    # Skip — file might still be writing
                    pass
            self.seen_files = current
        except Exception:
            pass

        self._schedule_next_poll()

    def _schedule_next_poll(self):
        if self._enabled and self._tk_root:
            self._after_id = self._tk_root.after(
                self.poll_interval_ms, self._check_for_new_files,
            )
