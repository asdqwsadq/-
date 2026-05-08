def like(field, value: str | None):
    if not value:
        return None
    return field.like(f"%{value}%")
