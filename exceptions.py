class CodeStatusException(Exception):
    """Ошибка статуса кода."""
    pass


class IncorrectResponseException(Exception):
    """АPI вернул ответ с ошибкой."""
    pass


class SendMessageException(Exception):
    """Произошла ошибка во время отправки сообщения в Телеграм."""
    pass
