def snake_case_to_camel_case(name: str) -> str:
    return name[0].lower() + name.replace("_", " ").title().replace(" ", "")[1:]


def normalize_name(name: str) -> str:
    return name.replace(" ", "_").replace("'", "")
