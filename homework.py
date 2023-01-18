from http import HTTPStatus
import logging
import os
import time

from dotenv import load_dotenv
import requests
import telegram

import exceptions


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

TOKEN_LIST = ['PRACTICUM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_TOKEN']
PARSE_STATUS = 'Изменился статус проверки работы "{}". {}'
GET_API_ANSWER = ('Ошибка запроса к API адресу: {},'
                  'link = {}, headers = {}, params = {}')
CHECK_RESPONSE_DICT = ('Возвращен неверный тип данных. Ожидается - dict,'
                       'а получен - {}')
CHECK_RESPONSE_LIST = ('Возвращен неверный тип данных. Ожидается - list,'
                       'а получен - {}')
PARSE_STATUS_ERROR = 'Получен неизвестный статус - {}.'
MAIN = 'Сбой в работе программы: {}'
MESSAGE_SENT = 'Бот отправил сообщение {}'
MESSAGE_SENT_ERROR = 'Ошибка отправки сообщения - {}({})'
BOT_STARTED = 'Бот запущен'
MISSING_TOKENS = 'Отсутствует(ют) токен(ы) - {}'
MISSING_HOMEWORK_NAME = 'Отсутствует имя домашней работы.'
MISSING_STATUS = 'Отсутствует статус работы.'
MISSING_HOMEWORK_KEY = 'Возвращен ответ без ключа homeworks'


def check_tokens():
    """.
    Проверяет доступность переменных окружения.
    """
    missed_tokens = [token for token in TOKEN_LIST if globals()[token] is None]
    if missed_tokens:
        logging.critical(MISSING_TOKENS.format(missed_tokens))
        raise ValueError(MISSING_TOKENS.format(missed_tokens))


def send_message(bot, message):
    """.
    Отправляет сообщение в Telegram чат.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SENT.format(message))
    except Exception as error:
        logging.exception(MESSAGE_SENT_ERROR.format(error, message))
        raise exceptions.SendMessageException(
            MESSAGE_SENT_ERROR.format(error, message))


def get_api_answer(timestamp):
    """.
    Делает запрос к единственному эндпоинту API-сервиса.
    """
    payload = {'from_date': timestamp}
    try:
        response_from_api = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=payload)
    except requests.RequestException as error:
        raise ConnectionError(
            GET_API_ANSWER.format(error, ENDPOINT, HEADERS, payload)
        )

    if response_from_api.status_code != HTTPStatus.OK:
        raise exceptions.CodeStatusException(
            GET_API_ANSWER.format(response_from_api.status_code, ENDPOINT,
                                  HEADERS, payload)
        )
    response = response_from_api.json()
    for error_word in ['error', 'code']:
        if error_word in response:
            raise exceptions.IncorrectResponseException(
                GET_API_ANSWER.format(error_word, ENDPOINT,
                                      HEADERS, payload))
    return response


def check_response(response):
    """.
    Проверяет ответ API на соответствие документации.
    """
    if not isinstance(response, dict):
        raise TypeError(CHECK_RESPONSE_DICT.format(type(response)))

    try:
        homeworks = response['homeworks']
    except KeyError:
        raise KeyError(MISSING_HOMEWORK_KEY)

    if not isinstance(homeworks, list):
        raise TypeError(CHECK_RESPONSE_LIST.format(type(response)))
    return homeworks


def parse_status(homework):
    """.
    Извлекает из информации о конкретной домашней работе статус этой работы
    """
    if 'homework_name' not in homework:
        raise KeyError(MISSING_HOMEWORK_NAME)
    if 'status' not in homework:
        raise KeyError(MISSING_STATUS)
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(PARSE_STATUS_ERROR.format(status))
    return PARSE_STATUS.format(homework.get('homework_name'),
                               HOMEWORK_VERDICTS[status])


def main():
    """Основная логика работы бота."""
    check_tokens()

    timestamp = 0
    bot = telegram.Bot(token=TELEGRAM_TOKEN)

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                continue
            message = parse_status(homeworks[0])
            send_message(bot, message)
            # не понимаю как это сделать
            timestamp = response.get('current_date',
                                     timestamp)
        except Exception as error:
            message = MAIN.format(error)
            logging.error(message)
            # и это
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    stream_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - '
               '%(lineno)s - %(message)s',
        handlers=(logging.StreamHandler(),
                  logging.FileHandler(filename=__file__ + '.log',
                                      mode='a', encoding=None, delay=False))
    )

    logging.info(BOT_STARTED)
    main()
    # from unittest import TestCase, mock, main as uni_main
    # ReqEx = requests.RequestException

    # class TestReq(TestCase):
    #     @mock.patch('requests.get')
    #     def test_raised(self, rq_get):
    #         rq_get.side_effect = mock.Mock(
    #             side_effect=ReqEx('testing'))
    #         main()
    # uni_main()

    # JSON = {'error': 'testing'}
    # class TestReq(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON)
    #         rq_get.return_value = resp
    #         main()
    # uni_main()

    # class TestReq(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.status_code = mock.Mock(
    #             return_value=333)
    #         rq_get.return_value = resp
    #         main()
    # uni_main()

    # JSON = {'homeworks': [{'homework_name': 'test', 'status': 'test'}]}
    # class TestReq(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON)
    #         rq_get.return_value = resp
    #         main()
    # uni_main()

    # JSON = {'homeworks': 1}
    # class TestReq(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON)
    #         rq_get.return_value = resp
    #         main()
    # uni_main()
