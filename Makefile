# vim:tabstop=8:noexpandtab:

.PHONY:

libexecdir!= if [ `uname` = 'FreeBSD' ]; then echo 'libexec'; else echo 'share'; fi
targetdir=$(DESTDIR)/$(PREFIX)/$(libexecdir)/igcollect

all:
	@echo "Dummy build target"

install:
	mkdir -p ${targetdir}
	mkdir -p ${targetdir}/libigcollect
	install src/*.py		${targetdir}
	install src/libigcollect/*.py	${targetdir}/libigcollect
