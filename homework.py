import os
import logging
import time

import telegram
import requests
from dotenv import load_dotenv

from exceptions import (EndpointError,
                        WrongFormatError, ExpectedStatusesError,
                        )

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(funcName)s - line %(lineno)s'
    ' - %(levelname)s - %(message)s'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens() -> bool:
    """Проверяем доступность переменных окружения.
    Которые необходимы для работы программы.
    """
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправляем сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение не отправлено: {telegram_error}')
    else:
        logger.debug(
            f'Сообщение отправлено: {message}')


def get_api_answer(timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса."""
    homework_statuses = None
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},  # 1549962000 - Время для отладки
        )                                       # 1670594662
        # homework_statuses.raise_for_status()
    except requests.exceptions.HTTPError as error:
        logger.error(f'Ответ API: {error}')
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != 200:
        message = (
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'StatusCode: {homework_statuses.status_code}')
        raise EndpointError(message)

    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if 'homeworks' in response:
        homework = response['homeworks']
    else:
        message = (
            'Ключ homeworks отсутствует при получения ответа от API '
        )
        raise TypeError(message)

    if 'current_date' not in response:
        message = (
            'Ключ current_date отсутствует при получения ответа от API '
        )
        raise TypeError(message)
    if homework is None:
        raise ValueError('Получен пустой ответ от API')
    if not isinstance(homework, list):
        message = 'В ответе API домашки представлены не списком'
        logger.error(message)
        raise WrongFormatError(message)
    return homework


def parse_status(homework):
    """Извлекает статус работы."""
    if not homework:
        message = (
            'Список с домишками пуст'
        )
        raise TypeError(message)
    else:
        if 'status' in homework:
            status = homework['status']
        else:
            message = (
                'Ключ status отсутствует при получения ответа от API '
            )
            raise KeyError(message)
        if 'homework_name' in homework:
            homework_name = homework['homework_name']
        else:
            message = (
                'Ключ homework_name отсутствует при получения ответа от API '
            )
            raise KeyError(message)

    if status not in HOMEWORK_VERDICTS:
        message = 'Недокументированный статус домашней работы'
        logger.error(message)
        raise ExpectedStatusesError(message)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует обязательный TOKEN или ID.')
        exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status_work = None

    while True:
        try:
            response = get_api_answer(timestamp)
        except EndpointError as error_response:
            send_message(bot, error_response)
            logger.error(error_response)
        else:
            try:
                homework = check_response(response)
                message = parse_status(homework[0])
                if status_work is None:
                    send_message(bot, message)
                    status_work = homework[0]['status']
            except TypeError as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.error(message)
            except ValueError as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.error(message)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
