import json
import os


class Translator:
    """Simple JSON-based i18n helper."""

    FALLBACK = "pt_BR"

    def __init__(self, language: str = "pt_BR", locale_dir: str | None = None):
        # Resolve locale directory: prefer explicit path, then same-level 'locale'
        if locale_dir is None:
            locale_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "locale",
            )
        self.locale_dir = locale_dir
        self.language = language
        self.translations: dict = {}
        self._load()

    def _load(self):
        path = os.path.join(self.locale_dir, self.language, "translation.json")
        if not os.path.exists(path):
            # Fallback to pt_BR
            path = os.path.join(self.locale_dir, self.FALLBACK, "translation.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except Exception:
            self.translations = {}

    def translate(self, key: str) -> str:
        return self.translations.get(key, key)

    def set_language(self, language: str):
        self.language = language
        self._load()
