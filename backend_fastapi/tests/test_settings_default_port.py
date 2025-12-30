from __future__ import annotations

import importlib


def test_default_port_is_8011() -> None:
    import app.settings as settings_mod

    importlib.reload(settings_mod)
    assert int(settings_mod.settings.port) == 8011
