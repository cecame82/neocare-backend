from datetime import date


def week_str_to_range(week_str: str):
    """
    Convierte 'YYYY-WW' en (start_date, end_date) donde start_date es lunes
    e end_date es domingo (ambos objetos datetime.date).

    Lanza ValueError si el formato o valores no son válidos.
    """
    if not week_str or "-" not in week_str:
        raise ValueError("Formato de semana inválido, se espera 'YYYY-WW'")

    parts = week_str.split("-")
    if len(parts) != 2:
        raise ValueError("Formato de semana inválido, se espera 'YYYY-WW'")

    year_part, week_part = parts[0], parts[1]
    try:
        year = int(year_part)
        week = int(week_part)
    except ValueError:
        raise ValueError("Año o número de semana no son enteros")

    # La función fromisocalendar lanza ValueError si la semana no existe
    # day 1 = Monday, day 7 = Sunday
    try:
        start = date.fromisocalendar(year, week, 1)
        end = date.fromisocalendar(year, week, 7)
    except Exception as exc:
        raise ValueError(f"Semana inválida: {exc}") from exc

    return start, end
