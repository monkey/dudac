all: $(NAME).duda

$(NAME).duda: $(OBJECTS)
	$(CC) $(CFLAGS) $(DEFS) -shared -o $@ $^ -lc $(LDFLAGS)

.c.o:
	$(CC) $(CFLAGS) $(DEFS) $(INCDIR) -fPIC -c $<

clean:
	rm -rf *.o *~ *.*duda*
