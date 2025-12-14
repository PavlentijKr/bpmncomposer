import json
import os
from typing import Any, Callable, Dict, Optional


class FieldInfo:
    def __init__(self, default: Any = None, env: Optional[str] = None, default_factory: Callable[[], Any] | None = None):
        self.default = default
        self.env = env
        self.default_factory = default_factory


def Field(default: Any = None, env: Optional[str] = None, default_factory: Callable[[], Any] | None = None):
    return FieldInfo(default=default, env=env, default_factory=default_factory)


def validator(*fields):
    def decorator(func: Callable):
        func.__validator_fields__ = fields
        return func

    return decorator


class BaseModelMeta(type):
    def __new__(mcls, name, bases, namespace):
        validators: Dict[str, list] = {}
        for attr, value in namespace.items():
            if callable(value) and hasattr(value, "__validator_fields__"):
                for field in value.__validator_fields__:
                    validators.setdefault(field, []).append(value)
        namespace["__validators__"] = validators
        return super().__new__(mcls, name, bases, namespace)


class BaseModel(metaclass=BaseModelMeta):
    __validators__: Dict[str, list]

    def __init__(self, **data):
        annotations = getattr(self, "__annotations__", {})
        for name, anno in annotations.items():
            value = data.get(name, getattr(self, name, None))
            if isinstance(value, FieldInfo):
                if value.default_factory is not None:
                    value = value.default_factory()
                else:
                    value = value.default
            for validator_fn in self.__validators__.get(name, []):
                value = validator_fn(self.__class__, value)  # type: ignore
            setattr(self, name, value)

    def dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("__")}

    def json(self):
        return json.dumps(self.dict(), ensure_ascii=False)

    @classmethod
    def parse_obj(cls, obj: Dict[str, Any]):
        return cls(**obj)


class BaseSettings(BaseModel):
    def __init__(self, **data):
        annotations = getattr(self, "__annotations__", {})
        new_data = {}
        for name, anno in annotations.items():
            field_value = getattr(self.__class__, name, None)
            if isinstance(field_value, FieldInfo) and field_value.env:
                env_value = os.getenv(field_value.env)
                if env_value is not None:
                    data[name] = self._cast(env_value, anno)
            if isinstance(field_value, FieldInfo) and name not in data:
                if field_value.default_factory is not None:
                    data[name] = field_value.default_factory()
                else:
                    data[name] = field_value.default
        data.update(new_data)
        super().__init__(**data)

    @staticmethod
    def _cast(value: str, target_type: Any):
        try:
            if target_type in (int, float, bool):
                return target_type(value)
        except Exception:
            return value
        return value
