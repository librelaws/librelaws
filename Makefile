init:
	pip install -r requirements.txt

test:
	py.test tests.py

.PHONY: init test
