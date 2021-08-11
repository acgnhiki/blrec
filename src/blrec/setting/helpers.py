from typing import TypeVar

from pydantic.main import BaseModel


__all__ = 'update_settings', 'shadow_settings'


_T = TypeVar('_T', bound=BaseModel)


def update_settings(src: _T, dst: _T) -> None:
    overwrite_settings(src, dst, exclude_unset=True)


def shadow_settings(src: _T, dst: _T) -> None:
    overwrite_settings(src, dst, exclude_none=True)


def overwrite_settings(
    src: _T, dst: _T, exclude_unset: bool = False, exclude_none: bool = False
) -> None:
    # XXX Caution! the src and dst should be the same model type
    assert isinstance(src, BaseModel) and isinstance(dst, BaseModel)

    fields = src.__fields_set__ if exclude_unset else src.__fields__

    for name in fields:
        if not hasattr(dst, name):
            continue
        value = getattr(src, name)
        if exclude_none and value is None:
            continue
        if not isinstance(value, BaseModel):
            setattr(dst, name, value)
        else:
            overwrite_settings(
                value,
                getattr(dst, name),
                exclude_unset=exclude_unset,
                exclude_none=exclude_none,
            )
