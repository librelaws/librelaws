init:
	pip install -r requirements.txt

test:
	py.test tests.py -vv

.PHONY: init test
