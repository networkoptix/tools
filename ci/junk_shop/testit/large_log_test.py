import logging


_logger = logging.getLogger(__name__)


LOG_RECORD_COUNT = 100000


def test_large_log():
    for i in range(LOG_RECORD_COUNT):
        _logger.info('Record #%06d: %s', i, '0123456789'*100)
