# vim:tabstop=8:noexpandtab:

.PHONY:

libexecdir!= if [ `uname` = 'FreeBSD' ]; then echo 'libexec'; else echo 'share'; fi
targetdir=$(DESTDIR)/$(PREFIX)

all:
	@echo "Dummy build target"

install:
	mkdir -p ${targetdir}/${libexecdir}/igcollect
	mkdir -p ${targetdir}/${libexecdir}/igcollect/libigcollect
	mkdir -p ${targetdir}/share/java
	install src/*.py		${targetdir}/${libexecdir}/igcollect
	install src/libigcollect/*.py	${targetdir}/${libexecdir}/igcollect/libigcollect
	install share/java/*.jar	${targetdir}/share/java
