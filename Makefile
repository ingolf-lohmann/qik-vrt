CC ?= cc
CFLAGS ?= -std=c89 -pedantic -Wall -Wextra -Iinclude
BIN = build/qikvrt_verify

all: $(BIN)

$(BIN): src/main.c src/qikvrt.c include/qikvrt.h
	mkdir -p build
	$(CC) $(CFLAGS) -o $(BIN) src/main.c src/qikvrt.c

test: all
	sh tests/run_all.sh

clean:
	rm -rf build

.PHONY: all test clean
