.PHONY: static

.DEFAULT: usage

usage:
	@echo "Usage:"
	@echo "    make static          # Import static data from other directories"

static:
	rm -rf examples/ && mkdir examples && cp ../examples/*.svg examples/
	rm -rf templates/ && cp -r ../termtosvg/data/templates .

