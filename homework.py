import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from http import HTTPStatus

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

PARSE_STATUS_PHRASE = 'Изменился статус проверки работы "{}". {}'


def check_tokens():
    """.
    Проверяет доступность переменных окружения.
    """
    token_list = [PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]
    for token in token_list:
        if token is None:
            logging.critical(f'Отсутствует токен - {token}')
    return all(token_list)


def send_message(bot, message):
    """.
    Отправляет сообщение в Telegram чат.
    """
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение {message}')
    except Exception as error:
        logging.exception(f'Ошибка отправки сообщения - {error}({message})')


def get_api_answer(timestamp):
    """.
    Делает запрос к единственному эндпоинту API-сервиса.
    """
    payload = {'from_date': timestamp}
    try:
        response_from_api = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=payload)
    except Exception as error:
        raise Exception(f'Ошибка запроса к API адресу: {error}'
                        f'link = {ENDPOINT}, '
                        f'headers = {HEADERS}, '
                        f'params = {payload}')

    if response_from_api.status_code != HTTPStatus.OK:
        raise Exception(
            f'Ошибка API запроса - {response_from_api.status_code}'
        )
    response = response_from_api.json()
    return response


def check_response(response):
    """.
    Проверяет ответ API на соответствие документации.
    """
    if not isinstance(response, dict):
        raise TypeError('Возвращен неверный тип данных. Ожидается - dict, '
                        f'а получен - {type(response)}')

    try:
        homeworks_list = response['homeworks']
        if not isinstance(homeworks_list, list):
            raise TypeError('Возвращен неверный тип данных. Ожидается - dict, '
                            f'а получен - {type(homeworks_list)}')
    except KeyError:
        raise KeyError('Возвращен ответ без ключа homeworks')
    return homeworks_list


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
        raise ValueError(f'Получен неизвестный статус - {status}.')
    verdict = HOMEWORK_VERDICTS[status]
    return PARSE_STATUS_PHRASE.format(homework_name, verdict)


def main():
    """.
    Основная логика работы бота.
    """
    last_send = {
        'error': None,
    }

    if not check_tokens():
        logging.critical('Отсутствуют все необходимые токены.')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if len(homeworks) == 0:
                logging.debug('Ответ API пуст: нет домашних работ.')
                break
            for homework in homeworks:
                message = parse_status(homework)
                if last_send.get(homework['homework_name']) != message:
                    send_message(bot, message)
                    last_send[homework['homework_name']] = message
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if last_send['error'] != message:
                send_message(bot, message)
                last_send['error'] = message
        else:
            last_send['error'] = None
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - '
                '%(lineno)s - %(message)s'),
        stream=sys.stdout,
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
