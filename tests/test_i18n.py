"""Tests for i18n translation support."""

from __future__ import annotations

from segy_toolbox.gui.i18n import get_locale, set_locale, tr


class TestI18n:
    def teardown_method(self):
        set_locale("ko")  # reset to default

    def test_default_locale_is_ko(self):
        assert get_locale() == "ko"

    def test_set_locale_en(self):
        set_locale("en")
        assert get_locale() == "en"

    def test_set_locale_invalid_ignored(self):
        set_locale("xx")
        assert get_locale() == "ko"

    def test_tr_korean(self):
        set_locale("ko")
        result = tr("open_file")
        assert "\ud30c\uc77c" in result  # Korean for "file"

    def test_tr_english(self):
        set_locale("en")
        assert tr("open_file") == "Open File"

    def test_tr_fallback_to_english(self):
        set_locale("ko")
        # If a key only exists in EN, it should fallback
        result = tr("nonexistent_key_xyz")
        assert result == "nonexistent_key_xyz"

    def test_tr_with_params(self):
        set_locale("en")
        result = tr("n_files_loaded", n=5)
        assert "5" in result

    def test_tr_korean_with_params(self):
        set_locale("ko")
        result = tr("n_files_loaded", n=3)
        assert "3" in result

    def test_all_en_keys_exist_in_ko(self):
        from segy_toolbox.gui.i18n import _EN, _KO
        missing = set(_EN.keys()) - set(_KO.keys())
        assert missing == set(), f"Keys missing in Korean: {missing}"

    def test_all_ko_keys_exist_in_en(self):
        from segy_toolbox.gui.i18n import _EN, _KO
        missing = set(_KO.keys()) - set(_EN.keys())
        assert missing == set(), f"Keys missing in English: {missing}"
