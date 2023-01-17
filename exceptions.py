class CodeStatusException(Exception):
    """Ошибка статуса кода."""
    pass


class IncorrectResponseException(Exception):
    """АPI вернул ответ с ошибкой."""
    pass
