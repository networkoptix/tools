import logging

log = logging.getLogger(__name__)


# produce user email list to send email to based on broken test list and configured test watcher list
def make_email_recipient_list(tests_watchers, build_info):

    def test_match_mask(test_path, test_mask):
        mask = test_mask.split('/')
        path = test_path.split('/')
        if mask[-1] == '*':
            return path[:len(mask) - 1] == mask[:-1]
        else:
            return path == mask

    def test_in_mask_list(test, mask_list):
        return any(test_match_mask(test, mask) for mask in mask_list)

    for name, twc in tests_watchers.items():
        if (build_info.failed_test_list and
            all(test_in_mask_list(test, twc.test_list) for test in build_info.failed_test_list)):
            log.info('All failed tests are in %r watcher list belonging to %r', name, twc.watcher_email)
            return [twc.watcher_email]
    email_list = build_info.changeset_email_list
    for name, twc in tests_watchers.items():
        if any(test_in_mask_list(test, twc.test_list) for test in build_info.failed_test_list):
            log.info('Some failed tests are in %r watcher list belonging to %r', name, twc.watcher_email)
            email_list.add(twc.watcher_email)
    return email_list
