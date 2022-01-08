import requests
import os
import logging
import time
import telegram

from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


class TokenError(Exception):
    """Ошибка.Отсутсвует один из токенов."""


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    logger.info('Отправляем в телеграм')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info('Сообщение успешно отправлено')
    except telegram.error.TelegramError as error:
        logger.error(f'Сообщение не удалось отправить. Ошибка {error}')


def get_api_answer(current_timestamp):
    """Получаем ответ от API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.OK:
        return response.json()
    else:
        logger.error('Эндпоинт недоступен')
        raise ConnectionError('Ошибка подключения')


def check_response(response):
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        logger.error('Неправильный тип ответа')
        raise TypeError('Ответ должен быть словарем')
    else:
        homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        logger.error('Неправильный тип ответа')
        raise TypeError('Домашки должны подаваться списком')
    return homeworks


def parse_status(homework):
    """Получаем статус ДЗ."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None or homework_status is None:
        logger.error('Отсутсвует ключ!')
        raise KeyError('Отсутсвует один из ключей!')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES.get(homework_status)
    else:
        logger.error('Статус работы неизвестен')
        raise KeyError('Неизвестный статус работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия токенов."""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID and PRACTICUM_TOKEN:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    logger.debug('Start!')
    if check_tokens is False:
        logger.critical('Один из токенов недоступен')
        raise TokenError
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    while True:
        try:
            logger.debug('Получаем ответ от API')
            response = get_api_answer(current_timestamp)
            logger.debug('Получаем домашние работы')
            homeworks = check_response(response)
            logger.debug('Ответ от API корректен')
            if homeworks:
                logger.info('Работы найдены')
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.info('Работы не найдены')
            current_timestamp = (response.get('current_date')
                                 or current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            time.sleep(60)


if __name__ == '__main__':
    main()
