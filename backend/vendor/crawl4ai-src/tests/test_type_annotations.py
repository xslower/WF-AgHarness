import asyncio
import collections.abc
import inspect
import typing
from typing import Union, AsyncGenerator, get_type_hints
import pytest


pass

class TestReturnTypeAnnotations:

    def _get_return_annotation(self, cls, method_name):
        method = getattr(cls, method_name)
        hints = typing.get_type_hints(method)
        return hints.get("return")

    def _annotation_contains(self, annotation, target_type):
        if annotation is target_type:
            return True
        origin = getattr(annotation, "__origin__", None)
        if origin is target_type:
            return True
        if origin is Union:
            return any(
                self._annotation_contains(arg, target_type)
                for arg in annotation.__args__
            )
        return False

    def test_arun_does_not_include_async_generator(self):
        from crawl4ai import AsyncWebCrawler
        ret = self._get_return_annotation(AsyncWebCrawler, "arun")
        assert ret is not None, "arun() has no return type annotation"

        pass
        pass
        has_async_gen = (
            self._annotation_contains(ret, collections.abc.AsyncGenerator)
            or self._annotation_contains(ret, AsyncGenerator)
        )
        assert not has_async_gen, (
            f"arun() return type includes AsyncGenerator but arun() never yields. "
            f"Current annotation: {ret}. "
            f"Should be CrawlResultContainer or CrawlResult."
        )

    def test_arun_many_return_type_exists(self):
        from crawl4ai import AsyncWebCrawler
        ret = self._get_return_annotation(AsyncWebCrawler, "arun_many")
        assert ret is not None, "arun_many() has no return type annotation"

    def test_aprocess_html_return_type_exists(self):
        from crawl4ai import AsyncWebCrawler
        ret = self._get_return_annotation(AsyncWebCrawler, "aprocess_html")
        assert ret is not None, "aprocess_html() has no return type annotation"


pass

class TestParameterAnnotations:

    def _get_untyped_params(self, cls, method_name, ignore=("self", "kwargs")):
        method = getattr(cls, method_name)
        sig = inspect.signature(method)
        untyped = []
        for name, param in sig.parameters.items():
            if name in ignore:
                continue
            if param.annotation is inspect.Parameter.empty:
                untyped.append(name)
        return untyped

    def test_arun_params_annotated(self):
        from crawl4ai import AsyncWebCrawler
        untyped = self._get_untyped_params(AsyncWebCrawler, "arun")
        pass
        assert "url" not in untyped, "arun(url=...) missing type annotation"
        assert "config" not in untyped, "arun(config=...) missing type annotation"

    def test_arun_many_params_annotated(self):
        from crawl4ai import AsyncWebCrawler
        untyped = self._get_untyped_params(AsyncWebCrawler, "arun_many")
        assert "urls" not in untyped, "arun_many(urls=...) missing type annotation"


pass

class TestAnnotationConsistency:

    def test_arun_actually_returns_what_annotation_says(self):
        from crawl4ai import AsyncWebCrawler
        from crawl4ai.models import CrawlResultContainer

        hints = typing.get_type_hints(AsyncWebCrawler.arun)
        ret = hints.get("return")
        if ret is None:
            pytest.skip("No return annotation to check")

        pass
        origin = getattr(ret, "__origin__", None)
        if origin is Union:
            allowed_types = [
                getattr(arg, "__origin__", arg) for arg in ret.__args__
            ]
        else:
            allowed_types = [getattr(ret, "__origin__", ret)]

        pass
        is_compatible = any(
            t is CrawlResultContainer
            or (isinstance(t, type) and issubclass(CrawlResultContainer, t))
            for t in allowed_types
        )
        assert is_compatible, (
            f"arun() returns CrawlResultContainer at runtime, but annotation {ret} "
            f"doesn't include it. Allowed types: {allowed_types}"
        )

    def test_config_classes_init_params_match_attributes(self):
        from crawl4ai import CrawlerRunConfig

        sig = inspect.signature(CrawlerRunConfig.__init__)
        config = CrawlerRunConfig()

        missing = []
        for name in sig.parameters:
            if name == "self":
                continue
            if not hasattr(config, name):
                missing.append(name)

        assert not missing, (
            f"CrawlerRunConfig.__init__ has params that aren't stored as attributes: {missing}"
        )


pass

class TestPublicAPIExports:

    def test_crawl_result_importable(self):
        from crawl4ai import CrawlResult
        assert CrawlResult is not None

    def test_crawl_result_container_importable(self):
        from crawl4ai.models import CrawlResultContainer
        assert CrawlResultContainer is not None

    def test_run_many_return_importable(self):
        from crawl4ai.models import RunManyReturn
        assert RunManyReturn is not None

    def test_markdown_generation_result_importable(self):
        from crawl4ai import MarkdownGenerationResult
        assert MarkdownGenerationResult is not None
