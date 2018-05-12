#
# igcollect - Makefile
#
# Copyright (c) 2018 InnoGames GmbH
#

.PHONY:

libexecdir!= if [ `uname` = 'FreeBSD' ]; then echo 'libexec'; else echo 'share'; fi
targetdir=$(DESTDIR)/$(PREFIX)

all:
	@echo "Dummy build target"

install: test
	mkdir -p ${targetdir}/${libexecdir}/igcollect
	mkdir -p ${targetdir}/${libexecdir}/igcollect/libigcollect
	mkdir -p ${targetdir}/share/java
	install src/*.py		${targetdir}/${libexecdir}/igcollect
	install src/libigcollect/*.py	${targetdir}/${libexecdir}/igcollect/libigcollect
	install share/java/*.jar	${targetdir}/share/java

test:
	pytest
