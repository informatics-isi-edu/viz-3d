subdirs := apps preprocessors

all:
	$(foreach dir,$(subdirs),cd ${dir}; make all;)

install:
	$(foreach dir,$(subdirs),cd ${dir}; make install;)

clean:
	$(foreach dir,$(subdirs),cd ${dir}; make clean;)
