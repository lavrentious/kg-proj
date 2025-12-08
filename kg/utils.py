def snake_case_to_camel_case(name: str) -> str:
    return name[0].lower() + name.replace("_", " ").title().replace(" ", "")[1:]


def normalize_name(name: str) -> str:
    return name.replace(" ", "_").replace("'", "")


def parse_value(value: str) -> float | None:
    if isinstance(value, (int, float)):
        return value

    s = str(value).strip()

    if s.endswith("%"):
        try:
            return float(s[:-1])
        except ValueError:
            return None

    if "/" in s:
        first = s.split("/")[0]
        try:
            return float(first)
        except ValueError:
            return None

    try:
        return float(s)
    except ValueError:
        return None
