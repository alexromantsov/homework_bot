import os
import logging
import time

import telegram
import requests

from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/' \
           ''
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
)


class EndpointError(Exception):
    """Когда API домашки возвращает код, отличный от 200."""

    pass


class LackExpectedKeys(Exception):
    """Отсутствие ожидаемых ключей в ответе API."""

    pass


class EmptyDictionary(Exception):
    """Пришел пустой словарь."""

    pass


class UnexpectedHomeworkStatus(Exception):
    """Получили неожиданный статус домашней работы."""

    pass


class WrongFormat(TypeError):
    """Структура данных не соответствует ожиданиям."""

    pass


class ExpectedStatuses(Exception):
    """Недокументированный статус домашней работы."""

    pass


def check_tokens():
    """Проверяем доступность переменных окружения.
    Которые необходимы для работы программы.
    """
    name_tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }

    for name, value in name_tokens.items():
        if not value:
            logger.critical(f'Отсутствует токен: {name}')
            raise SystemExit('Программа остановлена принудительно.')


def send_message(bot, message):
    """Отправляем сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(
            f'Сообщение отправлено: {message}')
    except telegram.TelegramError as telegram_error:
        logger.error(
            f'Сообщение не отправлено: {telegram_error}')


def get_api_answer(timestamp):
    """Делаем запрос к единственному эндпоинту API-сервиса."""
    homework_statuses = None
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp},  # 1549962000 - Время для отладки
        )  # 1670594662
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if homework_statuses.status_code != 200:
        message = (
            f'Эндпоинт недоступен. '
            f'StatusCode: {homework_statuses.status_code}')
        logger.error(message)
        raise EndpointError(message)

    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    try:
        homework = response['homeworks']
    except KeyError as error:
        message = (
            f'Отсутствует ключ {error} при получения ответа от API '
        )
        logger.error(message)
        raise LackExpectedKeys(message)
    if homework is None:
        message = (
            'Получен пустой ответ от API'
        )
        logger.error(message)
        raise LackExpectedKeys(message)
    if not homework:
        message = 'На данный момент нет домашек.'
        logger.info(message)
    if not isinstance(homework, list):
        message = 'В ответе API домашки представлены не списком'
        logger.error(message)
        raise WrongFormat(message)
    return homework[0]


def parse_status(homework):
    """Извлекает статус работы."""
    try:
        status = homework['status']
        homework_name = homework['homework_name']
    except KeyError as error:
        message = (
            f'Отсутствует ключ {error} при получения ответа от API '
        )
        logger.error(message)
        raise KeyError(message)

    if status not in HOMEWORK_VERDICTS:
        message = 'Недокументированный статус домашней работы'
        logger.error(message)
        raise ExpectedStatuses(message)
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    status_work = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if status_work is None:
                send_message(bot, message)
                status_work = homework['status']
            elif status_work != homework['status']:
                send_message(bot, message)
                status_work = homework['status']
            else:
                logger.debug('Статус домашки не обновился')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
