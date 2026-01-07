.PHONY: up down build logs backend frontend clean

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

backend:
	docker compose up --build backend

frontend:
	docker compose up --build frontend

clean:
	docker compose down --volumes --remove-orphans
