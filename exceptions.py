class EndpointError(Exception):
    """Когда API домашки возвращает код, отличный от 200."""

    pass

class IncorrectAnswerAPI(Exception):
    """Только логируем ошибку"""

    pass