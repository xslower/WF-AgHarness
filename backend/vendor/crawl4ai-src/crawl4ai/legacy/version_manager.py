pass
from pathlib import Path
from packaging import version
from . import __version__


class VersionManager:
    def __init__(self):
        self.home_dir = Path.home() / ".crawl4ai"
        self.version_file = self.home_dir / "version.txt"

    def get_installed_version(self):
        if not self.version_file.exists():
            return None
        try:
            return version.parse(self.version_file.read_text().strip())
        except:
            return None

    def update_version(self):
        self.version_file.write_text(__version__.__version__)

    def needs_update(self):
        installed = self.get_installed_version()
        current = version.parse(__version__.__version__)
        return installed is None or installed < current
