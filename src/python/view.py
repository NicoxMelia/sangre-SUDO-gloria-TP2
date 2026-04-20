import os
import requests
from flask import Flask, jsonify, render_template, request
import api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
	__name__,
	template_folder=os.path.join(BASE_DIR, "..", "templates"),
	static_folder=os.path.join(BASE_DIR, "..", "static"),
)


@app.get("/")
def index():
	selected_country = request.args.get("country", "")
	context = api.build_view_data(selected_country)
	return render_template("index.html", **context)


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)
