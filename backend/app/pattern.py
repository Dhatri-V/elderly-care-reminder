"""Parse dose patterns like "1-0-1", "½-0-1" or "0.5-0-1" (morning-afternoon-night)."""


def parse_pattern(text: str) -> tuple[float, float, float]:
    parts = text.replace(" ", "").split("-")
    if len(parts) != 3:
        raise ValueError("pattern must look like 1-0-1 (morning-afternoon-night)")

    doses = []
    for part in parts:
        if part.endswith("½"):
            part = (part[:-1] or "0") + ".5"
        try:
            dose = float(part)
        except ValueError:
            raise ValueError(f"invalid dose: {part!r}") from None
        if dose < 0 or dose > 10 or dose * 2 != int(dose * 2):
            raise ValueError(f"dose must be a whole or half tablet between 0 and 10: {part!r}")
        doses.append(dose)

    if sum(doses) == 0:
        raise ValueError("pattern needs at least one dose")
    return doses[0], doses[1], doses[2]
