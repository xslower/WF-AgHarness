from __future__ import annotations

from typing import Callable, Generic, Iterable, TypeVar

T = TypeVar("T")


class RegistryError(Exception):
    pass


class Registry(Generic[T]):

    def __init__(self, name: str, key: Callable[[T], str]) -> None:
        self.name = name
        self._key = key
        self._items: dict[str, T] = {}
        self._errors: dict[str, str] = {}
        self._frozen = False

    @property
    def frozen(self) -> bool:
        return self._frozen

    def register(self, item: T) -> T:
        if self._frozen:
            raise RegistryError(f"{self.name} 已冻结，禁止运行期注册")
        key = self._key(item)
        if not key:
            raise RegistryError(f"{self.name} 注册项缺少 key")
        if key in self._items:
            raise RegistryError(f"{self.name} 重复注册: {key}")
        self._items[key] = item
        return item

    def try_register(self, item: T, source: str = "") -> bool:
        try:
            self.register(item)
            return True
        except Exception as e:
            self._errors[source or self._key(item) or "unknown"] = f"{type(e).__name__}: {e}"
            return False

    def get(self, key: str) -> T | None:
        return self._items.get(key)

    def require(self, key: str) -> T:
        item = self.get(key)
        if item is None:
            raise RegistryError(f"{self.name} 未注册: {key}")
        return item

    def all(self) -> list[T]:
        return list(self._items.values())

    def keys(self) -> list[str]:
        return list(self._items.keys())

    def errors(self) -> dict[str, str]:
        return dict(self._errors)

    def freeze(self) -> None:
        self._frozen = True

    def clear(self) -> None:
        if self._frozen:
            raise RegistryError(f"{self.name} 已冻结，禁止清空")
        self._items.clear()
        self._errors.clear()
