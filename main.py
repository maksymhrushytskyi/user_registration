import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv
from flask import Flask, request, render_template_string, send_from_directory
import psycopg


load_dotenv()


@dataclass
class Config:
	db_url: str


def get_config() -> Config:
	url = os.getenv("DB_URL")
	if not url:
		raise RuntimeError("DB_URL is not set in environment")
	return Config(db_url=url)


def create_app() -> Flask:
	app = Flask(__name__)

	@app.post("/register")
	def register():
		data = {
			"name": request.form.get("name"),
			"familyname": request.form.get("familyname"),
			"callphone": request.form.get("callphone"),
			"email": request.form.get("email"),
			"mom_name": request.form.get("mom_name"),
			"mom_family_name": request.form.get("mom_family_name"),
			"first_pet": request.form.get("first_pet"),
		}

		# Basic validation
		missing = [k for k, v in data.items() if not v]
		if missing:
			return {"ok": False, "error": f"Missing: {', '.join(missing)}"}, 400

		insert_sql = (
			"""
			INSERT INTO registrations
			(name, familyname, callphone, email, mom_name, mom_family_name, first_pet)
			VALUES (%(name)s, %(familyname)s, %(callphone)s, %(email)s, %(mom_name)s, %(mom_family_name)s, %(first_pet)s)
			RETURNING id
			"""
		)

		cfg_local = get_config()
		try:
			with psycopg.connect(cfg_local.db_url) as conn:
				with conn.cursor() as cur:
					# Ensure table exists at request time
					cur.execute(
						"""
						CREATE TABLE IF NOT EXISTS registrations (
							id SERIAL PRIMARY KEY,
							name TEXT NOT NULL,
							familyname TEXT NOT NULL,
							callphone TEXT NOT NULL,
							email TEXT NOT NULL,
							mom_name TEXT NOT NULL,
							mom_family_name TEXT NOT NULL,
							first_pet TEXT NOT NULL,
							created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
						);
						"""
					)
					cur.execute(insert_sql, data)
					new_id = cur.fetchone()[0]
				conn.commit()
		except Exception as e:
			return {"ok": False, "error": str(e)}, 500

		# Simple thank-you page
		html = """
		<!doctype html>
		<html lang="uk">
		<head><meta charset="utf-8"><title>Успіх</title></head>
		<body>
		<h2>Дякуємо за реєстрацію!</h2>
		<p>Ваш номер заявки: {{ id }}</p>
		<a href="/">Повернутись</a>
		</body>
		</html>
		"""
		return render_template_string(html, id=new_id)

	@app.get("/")
	def root():
		# Serve the static index.html
		try:
			with open(os.path.join(os.path.dirname(__file__), "index.html"), "r", encoding="utf-8") as f:
				return f.read()
		except Exception:
			return "Index not found", 404

	@app.get("/style.css")
	def style_css():
		# Serve the CSS for the page
		return send_from_directory(os.path.dirname(__file__), "style.css")

	return app


if __name__ == "__main__":
	app = create_app()
	# For local dev only
	app.run(host="127.0.0.1", port=5000, debug=True)

