from flask import render_template
from junk_shop.webapp import app


@app.route('/robots.txt')
def robots_txt():
    return render_template('robots.txt')
