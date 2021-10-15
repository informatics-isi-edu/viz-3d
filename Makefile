subdirs := apps preprocessors
targets := all install clean

$(targets): $(subdirs)
$(subdirs):
	$(MAKE) -C $@ $(MAKECMDGOALS)

.PHONY: $(targets) $(subdirs)
