class Printer(object):
    def __init__(self):
        pass

    def user_title(self, user_id, name, total_count):
        pass

    def review_list(self, caption, reviews):
        pass

    def total(self, total_count):
        print('Total reviews to cleanup: {}'.format(total_count))


class TxtPrinter(Printer):
    def __init__(self):
        super(TxtPrinter, self).__init__()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        print('')

    def user_title(self, user_id, name, total_count):
        print('{} ({})'.format(name, total_count))
        print('')

    def review_list(self, caption, reviews):
        if not reviews:
            return

        reviews.sort(key=lambda r: -r.age)
        print('  {} ({}): {}'.format(caption, len(reviews), ', '.join([
            '{} ({} days)'.format(r.id, r.age.days) for r in reviews])))
        print('')


class HtmlPrinter(Printer):
    def __init__(self, url):
        self.url = url

    def __enter__(self):
        print('''<html>
<head>
    <link rel="stylesheet" type="text/css"
      href="http://enk.me:8082/~f566efe912e8c5b2ce7921c0947807ce/assets/application.6eb61ec9fe8401910b4a.css">
    <style>
    body {
        margin: 32px;
    }
</style>
</head>
<body>''')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        print('</body></html>')

    def user_title(self, user_id, name, total_count):
        user_link = '{0}/user/{1}?tab=reviews'.format(self.url, user_id)
        print('<h3>{0} (<a href="{1}">{2}</a>)</h3>'
              .format(name, user_link, total_count))

    def review_list(self, caption, reviews):
        if not reviews:
            return

        def review_link(review):
            return '{0}/{1}/review/{2}'.format(self.url, review.project_id, review.id)

        reviews.sort(key=lambda r: -r.age)
        print('<h4>{0} ({1})</h4>'.format(caption, len(reviews)))
        print('<ul>')
        for r in reviews:
            print('<li><a href="{0}">{1}</a> ({2} days)</li>'
                  .format(review_link(r), r.id, r.age.days))
        print('</ul>')
