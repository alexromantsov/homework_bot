class EndpointError(Exception):
    """Когда API домашки возвращает код, отличный от 200."""

    pass


class WrongFormatError(TypeError):
    """Структура данных не соответствует ожиданиям."""

    pass
