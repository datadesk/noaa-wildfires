.PHONY: lint test ship

lint:
	pipenv run flake8 ./

test:
	pipenv run coverage run test.py
	pipenv run coverage report -m

scrape:
	pipenv run noaawildfires hms-fires > data/hms-fires.json
	pipenv run noaawildfires hms-smoke > data/hms-smoke.json

ship:
	rm -rf build/
	rm -rf dist/
	pipenv run python setup.py sdist bdist_wheel
	pipenv run twine upload dist/* --skip-existing
