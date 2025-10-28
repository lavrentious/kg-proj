def snake_case_to_camel_case(name: str) -> str:
    return name[0].lower() + name.replace("_", " ").title().replace(" ", "")[1:]
