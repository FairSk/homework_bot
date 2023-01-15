import json
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

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
handler_CP1251 = logging.FileHandler(filename='cp1251.log')
handler_UTF8 = logging.FileHandler(filename='program.log', encoding='utf-8')
logging.basicConfig(
    level=logging.DEBUG,
    handlers=(handler_UTF8, handler_CP1251),
    format=('%(asctime)s - %(levelname)s '
            '- %(name)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
logger.setLevel(logging.ERROR)
logger.setLevel(logging.CRITICAL)

handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)

formatter = logging.Formatter('%(asctime)s - %(levelname)s '
                              '- %(name)s - %(message)s')
handler.setFormatter(formatter)


def check_tokens():
    """.
    Проверяет доступность переменных окружения.
    """
    if (PRACTICUM_TOKEN or TELEGRAM_CHAT_ID or TELEGRAM_TOKEN) is None:
        return False
    return True


def send_message(bot, message):
    """.
    Отправляет сообщение в Telegram чат.
    """
    try:
        logging.debug(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """.
    Делает запрос к единственному эндпоинту API-сервиса.
    """
    PAYLOAD = {'from_date': timestamp}
    try:
        response_from_api = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=PAYLOAD)
    except Exception as error:
        logger.error(f'Ошибка запроса к API адресу: {error}')
    if response_from_api.status_code != HTTPStatus.OK:
        logger.error(
            f'Ошибка API запроса - {response_from_api.status_code}'
        )
        raise Exception(
            f'Ошибка API запроса - {response_from_api.status_code}'
        )
    try:
        response = response_from_api.json()
    except json.JSONDecodeError as error:
        logger.error(
            f'Ответ от API адреса не преобразован в json(): {error}.'
        )
    return response


def check_response(response):
    """.
    Проверяет ответ API на соответствие документации.
    """
    if not isinstance(response, dict):
        logger.error('Возвращен неверный тип данных.')
        raise TypeError('Возвращен неверный тип данных.')

    try:
        homeworks_list = response['homeworks']
        if not isinstance(homeworks_list, list):
            logger.error('Возвращен неверный тип данных.')
            raise TypeError('Возвращен неверный тип данных.')
    except KeyError:
        logger.error('Возвращен ответ без ключа homeworks')
        raise KeyError('Возвращен ответ без ключа homeworks')

    try:
        homework = homeworks_list[0]
    except IndexError:
        logger.error('Список пуст.')
        raise IndexError('Список пуст.')
    return homework


def parse_status(homework):
    """.
    Извлекает из информации о конкретной домашней работе статус этой работы
    """
    if 'homework_name' not in homework:
        logger.error('Отсутствует статус д/з.')
        raise KeyError('Отсутствует статус д/з.')
    if 'status' not in homework:
        logger.error('Отсутствует статус.')
        raise KeyError('Отсутствует статус.')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        logger.error('Получен неизвестный статус.')
        raise KeyError('Получен неизвестный статус.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """.
    Основная логика работы бота.
    """
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_status = ''
    previous_error = ''
    flag = True

    if not check_tokens():
        logger.critical('Недостаточно токенов для запуска бота.')
        flag = False

    while flag:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homework = check_response(response)
            message = parse_status(homework)
            if message != previous_status:
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)
        except Exception as error:
            logger.error(error)
            error_message = f'Ошибка - {error}'
            if error_message != previous_error:
                send_message(bot, error_message)
                previous_error = error_message
            time.sleep(RETRY_PERIOD)
        else:
            response = get_api_answer(timestamp)
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
