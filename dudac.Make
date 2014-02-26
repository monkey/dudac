_PATH     = $(patsubst /%, %, $(CURDIR))
_CC       = @echo "  [CC]   $@"; $(CC)
_DD       = @echo "  [DD]   $@"; $(CC)
_CC_QUIET = @echo -n; $(CC)

all: $(NAME).duda

$(NAME).duda: $(OBJECTS)
	$(_DD) $(CFLAGS) $(DEFS) -shared -o $@ $^ -lc $(LDFLAGS)

.c.o:
	$(_CC) -c $(CFLAGS) $(DEFS) $(INCDIR) -fPIC $<
	$(_CC_QUIET) -MM -MP $(CFLAGS) $(DEFS) $(INCDIR) $*.c -o $*.d > /dev/null &2>&1

clean:
	rm -rf *.o *.d *~ $(NAME).duda
