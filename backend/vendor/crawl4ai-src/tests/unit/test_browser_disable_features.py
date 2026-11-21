
from crawl4ai import BrowserConfig
from crawl4ai.browser_manager import BrowserManager, ManagedBrowser


def _disable_feature_names(args):
    names = []
    for arg in args:
        if arg.startswith("--disable-features="):
            names.extend(
                name.strip()
                for name in arg.split("=", 1)[1].split(",")
                if name.strip()
            )
    return names


def test_build_browser_flags_omits_optimization_hints():
    config = BrowserConfig(headless=True)
    names = _disable_feature_names(ManagedBrowser.build_browser_flags(config))
    assert "OptimizationHints" not in names
    assert "MediaRouter" in names
    assert "DialMediaRouteProvider" in names


def test_build_browser_args_omits_optimization_hints():
    config = BrowserConfig(headless=True)
    args = BrowserManager(browser_config=config)._build_browser_args()["args"]
    names = _disable_feature_names(args)
    assert "OptimizationHints" not in names
    assert "MediaRouter" in names
    assert "DialMediaRouteProvider" in names


def test_light_mode_still_omits_optimization_hints():
    config = BrowserConfig(headless=True, light_mode=True)
    for flags in (
        ManagedBrowser.build_browser_flags(config),
        BrowserManager(browser_config=config)._build_browser_args()["args"],
    ):
        names = _disable_feature_names(flags)
        assert "OptimizationHints" not in names
        assert "MediaRouter" in names
        assert "DialMediaRouteProvider" in names
