#ifndef UTIL_H
#define UTIL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>

/* A dynamic buffer. */
struct dynbuf {
	/* Start of buffer. */
	void *ptr;
	/* Size. */
	size_t size;
	/* Capacity of the underlying allocation. */
	size_t cap;
	/* Read/write offset. */
	size_t off;
	/* Whether we own the underlying allocation. */
	bool owned;
};

/**
 * Reads exactly |count| bytes from |fd| into |buf|.
 * Return true on success, false otherwise.
 */
bool read_exactly(int fd, void *buf, size_t count);

/**
 * Writes exactly |count| bytes to |fd| from |buf|.
 * Return true on success, false otherwise.
 */
bool write_exactly(int fd, const void *buf, size_t count);

/**
 * Resolves a TCP hostname and port.
 * On success, returns an addrinfo list to be freed by freeaddrinfo().
 * On failure, returns NULL.
 */
struct addrinfo *resolve_host(const char *host, uint16_t port);

/**
 * Reads the file at |path|.
 * On success, returns the contents, to be freed by free(), and stores the
 * file size in |size| (if not NULL). The contents are NUL-terminated.
 * On failure, returns NULL and |size| is undefined.
 */
char *read_file(const char *path, size_t *size);

/**
 * Writes |size| bytes from |content| to the file at |path|.
 * If the file exists, it is overwritten.
 * Return true on success, false otherwise.
 */
bool write_file(const char *path, const void *content, size_t size);

/**
 * Generates a random alphanumeric string of length |length| into |s|.
 * Returns true on success, false otherwise.
 */
bool rand_alnum(char *s, size_t length);

/**
 * Converts a numeric string in base |base| to unsigned long.
 * On success, returns true and stores the value in |value|.
 * On failure, returns false and |value| is undefined.
 */
bool strtoul_checked(const char *s, int base, unsigned long *value);

/**
 * Writes the hex-encoded string of |buf| of size |size| into |out|.
 */
void hexencode(char *out, const void *buf, size_t size);

/**
 * Fills |buf| with the hex-decoded data from string |s|.
 * Returns true on success, false otherwise.
 */
bool hexdecode(void *buf, const char *s);

/**
 * Initializes a dynamic buffer.
 * Returns true on success, false otherwise.
 */
void dynbuf_init(struct dynbuf *buf);

/**
 * Initializes a dynamic buffer from an existing buffer |ptr| of size |size|.
 * If owned is true, then |ptr| must be a pointer returned by malloc() and
 * the dynamic buffer takes ownership of the allocation.
 * If owned is false, the buffer cannot be reallocated on write.
 */
void dynbuf_init_mem(struct dynbuf *buf, void *ptr, size_t size, bool owned);

/**
 * Writes |size| bytes into |buf|.
 * On success, returns a pointer to the reserved data area.
 * On failure, returns NULL.
 */
void *dynbuf_write(struct dynbuf *buf, size_t size);

/**
 * Reads |size| bytes from |buf|.
 * On success, returns a pointer to the data.
 * On failure, returns NULL.
 */
const void *dynbuf_read(struct dynbuf *buf, size_t size);

/**
 * Writes |size| bytes from |src| into |buf|.
 * Returns true on success, false otherwise.
 */
bool dynbuf_write_data(struct dynbuf *buf, const void *src, size_t size);

/**
 * Reads |size| bytes from |buf| into |dst|.
 * Returns true on success, false otherwise.
 */
bool dynbuf_read_data(struct dynbuf *buf, void *dst, size_t size);

/**
 * Resets |buf|, releasing the underlying allocation to the caller.
 * Passing NULL results in a NULL return.
 */
void *dynbuf_release(struct dynbuf *buf);

/**
 * Resets |buf|, freeing any allocated memory if the buffer is owned.
 * Passing NULL results in a no-op.
 */
void dynbuf_reset(struct dynbuf *buf);

#endif
