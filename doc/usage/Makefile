
PICS = mdrun_test.png


pics: $(PICS)

%.png: %.dot
	dot -T png $< > $@
