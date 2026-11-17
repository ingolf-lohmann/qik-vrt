/* SPDX-License-Identifier: Apache-2.0
 * Compatibility for a PID namespace with a host-mounted procfs.
 * Only the current process executable lookup is redirected. No proof,
 * filesystem admission, source, digest or kernel function is intercepted.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

ssize_t readlink(const char *path, char *buffer, size_t size) {
    ssize_t (*original)(const char *, char *, size_t);
    *(void **)(&original) = dlsym(RTLD_NEXT, "readlink");
    char current[64];
    snprintf(current, sizeof current, "/proc/%ld/exe", (long)getpid());
    if (strcmp(path, current) == 0) path = "/proc/self/exe";
    return original(path, buffer, size);
}
