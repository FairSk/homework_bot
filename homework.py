from http import HTTPStatus
import logging
import os
import sys
import time


from dotenv import load_dotenv
import requests
import telegram

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
CHECK_RESPONSE = ('Возвращен неверный тип данных. Ожидается - dict,'
                  'а получен - {}')
PARSE_STATUS_ERROR = 'Получен неизвестный статус - {}.'
MAIN = 'Сбой в работе программы: {}'
MESSAGE_SENT = 'Бот отправил сообщение {}'
MESSAGE_SENT_ERROR = 'Ошибка отправки сообщения - {}({})'


def check_tokens():
    """.
    Проверяет доступность переменных окружения.
    """
    missed_tokens = []
    for token in TOKEN_LIST:
        if globals()[token] is None:
            missed_tokens += token
    if len(missed_tokens) > 0:
        logging.critical(f'Отсутствует(ют) токен(ы) - {missed_tokens}')
        return False
    else:
        return True


def send_message(bot, message):
    """.
    Отправляет сообщение в Telegram чат.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(MESSAGE_SENT.format(message))
    except Exception as error:
        logging.exception(MESSAGE_SENT_ERROR.format(error, message))


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
        raise StatusCodeError(
            GET_API_ANSWER.format(response_from_api.status_code, ENDPOINT,
                                  HEADERS, payload)
        )
    response = response_from_api.json()
    if response.get('error') or response.get('code') is not None:
        raise ValueError(GET_API_ANSWER.format(response, ENDPOINT,
                                               HEADERS, payload))
    return response


def check_response(response):
    """.
    Проверяет ответ API на соответствие документации.
    """
    if not isinstance(response, dict):
        raise TypeError(CHECK_RESPONSE.format(type(response)))

    try:
        homeworks = response['homeworks']
        if not isinstance(homeworks, list):
            raise TypeError(CHECK_RESPONSE.format(type(response)))
    except KeyError:
        raise KeyError('Возвращен ответ без ключа homeworks')
    return homeworks[0]


def parse_status(homework):
    """.
    Извлекает из информации о конкретной домашней работе статус этой работы
    """
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует имя домашней работы.')
    if 'status' not in homework:
        raise KeyError('Отсутствует статус.')
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS.keys():
        raise ValueError(PARSE_STATUS_ERROR.format(status))
    return PARSE_STATUS.format(homework_name, HOMEWORK_VERDICTS[status])


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time()) - 24 * 60 * 60
    status_message = ''
    error_message = ''
    if not check_tokens():
        logging.critical('Отсутствуют токены')
        sys.exit(1)

    while True:
        try:
            bot = telegram.Bot(token=TELEGRAM_TOKEN)
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            message = parse_status(check_response(response))
            if message != status_message:
                send_message(bot, message)
                status_message = message
        except Exception as error:
            logging.error(error)
            message = f'Сбой в работе программы: {error}'
            if message != error_message:
                send_message(bot, message)
                error_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - '
                '%(lineno)s - %(message)s'),
        filename='main.log',
    )
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
