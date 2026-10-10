.PHONY: run test deb icons clean
run:
	PYTHONPATH=src python3 -m pixel_td
test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
deb:
	./packaging/debian/build-deb.sh
icons:
	python3 tools/make_icon.py
clean:
	rm -rf build dist *.egg-info src/*.egg-info
