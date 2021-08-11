import re


def snake_case(string: str) -> str:
    return re.sub(
        r'([a-z])([A-Z])',
        lambda m: m.group(1) + '_' + m.group(2).lower(),
        string
    )


def camel_case(string: str) -> str:
    words = string.split('_')
    return ''.join(
        [words[0].casefold()] + [word.capitalize() for word in words[1:]]
    )
