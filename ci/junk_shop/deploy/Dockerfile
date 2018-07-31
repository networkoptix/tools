FROM tiangolo/uwsgi-nginx-flask:python2.7

RUN apt-get update \
	&& apt-get install -y libpq-dev

COPY ./requirements.txt /tmp/
RUN pip install --upgrade pip
RUN pip install --requirement /tmp/requirements.txt

COPY junk_shop /app/junk_shop
COPY deploy/uwsgi.ini /app/uwsgi.ini
COPY deploy/settings.py /app/settings.py

ADD https://cdn.plot.ly/plotly-latest.min.js /app/junk_shop/webapp/static/
RUN chmod 0644 /app/junk_shop/webapp/static/plotly-latest.min.js
