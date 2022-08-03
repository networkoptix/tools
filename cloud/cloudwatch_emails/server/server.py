from flask import Flask, jsonify, request, send_from_directory
from .email_reader import main
app = Flask(__name__, static_folder="static")


@app.route("/email_report.json")
def report():
	return jsonify(main())


@app.route("/<file_name>")
def manifest(file_name=None):
	return send_from_directory("static", file_name)


@app.route('/')
def index():
	return send_from_directory("static", "index.html")
