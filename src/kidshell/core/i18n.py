"""Internationalization support for kidshell."""

from typing import Any


class I18n:
    """Handle internationalization and translation."""

    def __init__(self, language: str = "en"):
        """
        Initialize I18n with specified language.

        Args:
            language: Language code (e.g., "en", "zh_CN")
        """
        self.language = language
        self.translations = {
            "en": {
                "today_is": "Today is",
                "date_format": "%A, %B %d",
                "birthday_msg": "My birthday is {year}-{month}-{day}.",
                "age_msg": "Today, I am {age:.02f} years old.",
                "next_birthday": "I will be {age} years old in {days} days.",
                "bye": "Bye Bye!",
                "ok": "OK",
                "stop": "Stop",
                "add_symbol": "Add Symbol:",
                "found_symbol": "Found Symbol:",
                "great_options": ["Great", "Awesome", "Amazing", "Wonderful"],
            },
            "zh_CN": {
                "today_is": "今天是",
                "date_format": "%Y-%m-%d",
                "birthday_msg": "My birthday is {year}-{month}-{day}.\n我的生日是 {year}年 {month}月 {day}号。",
                "age_msg": "Today, I am {age:.02f} years old.\n今天，我是 {age:.02f} 岁。",
                "next_birthday": "I will be {age} years old in {days} days. 过{days}天, 我就是{age}岁了。",
                "bye": "再见 Bye Bye!",
                "ok": "好了 OK",
                "stop": "停 Stop",
                "add_symbol": "Add Symbol 新符号:",
                "found_symbol": "Found Symbol 符号:",
                "great_options": ["好棒", "真棒", "精彩", "奇妙", "Great", "Awesome"],
            },
        }

    def get(self, key: str, **kwargs: Any) -> str:
        """
        Get translated string for the given key.

        Args:
            key: Translation key
            **kwargs: Format arguments for the string

        Returns:
            Translated and formatted string
        """
        lang_dict = self.translations.get(self.language, self.translations["en"])
        template = lang_dict.get(key, self.translations["en"].get(key, key))

        if kwargs:
            return template.format(**kwargs)
        return template

    def get_list(self, key: str) -> list[str]:
        """
        Get translated list for the given key.

        Args:
            key: Translation key for a list

        Returns:
            Translated list
        """
        lang_dict = self.translations.get(self.language, self.translations["en"])
        return lang_dict.get(key, self.translations["en"].get(key, []))


# Global I18n instance
_i18n = I18n()


def set_language(language: str) -> None:
    """Set the global language."""
    global _i18n
    _i18n = I18n(language)


def t(key: str, **kwargs: Any) -> str:
    """Translate a string."""
    return _i18n.get(key, **kwargs)


def t_list(key: str) -> list[str]:
    """Get a translated list."""
    return _i18n.get_list(key)
