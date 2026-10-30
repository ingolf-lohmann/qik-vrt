/* SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0 */
/* Copyright 2026 Ingolf Lohmann. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
/* Lean 4.19 uses /proc/getpid()/exe. The container exposes host procfs.
 * Redirect ONLY this process's executable lookup to procfs's self alias.
 * No Lean parser, elaborator, proof term or kernel operation is replaced. */
ssize_t readlink(const char *path, char *buf, size_t size) {
    ssize_t (*original)(const char *, char *, size_t);
    char own[64];
    *(void **)(&original) = dlsym(RTLD_NEXT, "readlink");
    snprintf(own, sizeof own, "/proc/%ld/exe", (long)getpid());
    return original(strcmp(path, own) == 0 ? "/proc/self/exe" : path, buf, size);
}
