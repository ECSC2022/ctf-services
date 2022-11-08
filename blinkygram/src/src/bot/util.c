#define _GNU_SOURCE             /* TEMP_FAILURE_RETRY */
#define _POSIX_C_SOURCE 200112L /* addrinfo */

#include "util.h"

#include <errno.h>
#include <inttypes.h>
#include <netdb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <unistd.h>

/* Alphanumeric alphabet. */
static const char alnum_alpha[] =
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";

/* Initial capacity for dynbuf. */
#define DYNBUF_INITIAL_CAP 64

static char hexencode_digit(unsigned nibble)
{
	return nibble <= 9 ? '0' + nibble : 'a' + (nibble - 10);
}

static bool hexdecode_digit(char digit, unsigned *value)
{
	if (digit >= '0' && digit <= '9')
		*value = digit - '0';
	else if (digit >= 'a' && digit <= 'f')
		*value = digit - 'a' + 10;
	else if (digit >= 'A' && digit <= 'F')
		*value = digit - 'A' + 10;
	else
		return false;
	return true;
}

bool read_exactly(int fd, void *buf, size_t count)
{
	size_t done = 0;
	while (done < count) {
		ssize_t ret =
		    TEMP_FAILURE_RETRY(read(fd, (char *)buf + done, count - done));
		if (ret == -1) {
			perror("read");
			return false;
		}
		if (ret == 0)
			return false;
		done += ret;
	}
	return true;
}

bool write_exactly(int fd, const void *buf, size_t count)
{
	size_t done = 0;
	while (done < count) {
		ssize_t ret =
		    TEMP_FAILURE_RETRY(write(fd, (char *)buf + done, count - done));
		if (ret == -1) {
			perror("write");
			return false;
		}
		if (ret == 0)
			return false;
		done += ret;
	}
	return true;
}

struct addrinfo *resolve_host(const char *host, uint16_t port)
{
	char port_buf[6];
	sprintf(port_buf, "%" PRIu16, port);

	struct addrinfo hints = {
	    .ai_family = AF_UNSPEC,
	    .ai_socktype = SOCK_STREAM,
	    .ai_protocol = IPPROTO_TCP,
	};

	struct addrinfo *addrs;
	int ret = getaddrinfo(host, port_buf, &hints, &addrs);
	if (ret) {
		if (ret == EAI_SYSTEM)
			perror("getaddrinfo");
		else
			fprintf(stderr, "getaddrinfo: %s\n", gai_strerror(ret));
		return NULL;
	}

	if (!addrs)
		fprintf(stderr, "resolve_host: cannot resolve\n");

	return addrs;
}

char *read_file(const char *path, size_t *size)
{
	bool success = false;
	FILE *fp = NULL;
	char *buf = NULL;

	fp = fopen(path, "r");
	if (!fp) {
		perror("fopen");
		goto cleanup;
	}

	if (fseek(fp, 0, SEEK_END) == -1) {
		perror("fseek");
		goto cleanup;
	}

	long end_pos = ftell(fp);
	if (end_pos == -1) {
		perror("ftell");
		goto cleanup;
	}

	if (fseek(fp, 0, SEEK_SET) == -1) {
		perror("fseek");
		goto cleanup;
	}

	buf = malloc(end_pos + 1);
	if (!buf) {
		perror("malloc");
		goto cleanup;
	}

	if (fread(buf, 1, end_pos, fp) != (size_t)end_pos) {
		perror("fread");
		goto cleanup;
	}
	buf[end_pos] = '\0';

	if (size)
		*size = end_pos;

	success = true;

cleanup:
	if (fp)
		fclose(fp);
	if (!success)
		free(buf);
	return success ? buf : NULL;
}

bool write_file(const char *path, const void *content, size_t size)
{
	bool ret = false;
	FILE *fp = NULL;

	fp = fopen(path, "w");
	if (!fp) {
		perror("fopen");
		goto cleanup;
	}

	if (fwrite(content, 1, size, fp) != size) {
		perror("fwrite");
		goto cleanup;
	}

	ret = true;

cleanup:
	if (fp)
		fclose(fp);
	return ret;
}

bool rand_alnum(char *s, size_t length)
{
	if (getrandom(s, length, 0) == -1) {
		perror("getrandom");
		return false;
	}

	unsigned char *p = (void *)s;
	for (size_t i = 0; i < length; i++)
		s[i] = alnum_alpha[p[i] % (sizeof(alnum_alpha) - 1)];
	s[length] = '\0';

	return true;
}

bool strtoul_checked(const char *s, int base, unsigned long *value)
{
	errno = 0;
	char *endptr;
	*value = strtoul(s, &endptr, base);
	if (errno) {
		perror("strtoul");
		return false;
	}
	if (*endptr)
		return false;
	return true;
}

void hexencode(char *out, const void *buf, size_t size)
{
	for (size_t i = 0; i < size; i++) {
		unsigned char byte = ((unsigned char *)buf)[i];
		*out++ = hexencode_digit(byte >> 4);
		*out++ = hexencode_digit(byte & 0xf);
	}
	*out = '\0';
}

bool hexdecode(void *buf, const char *s)
{
	unsigned char *p = buf;
	while (*s) {
		unsigned high, low;
		if (!hexdecode_digit(*s++, &high))
			return false;
		if (!*s)
			return false;
		if (!hexdecode_digit(*s++, &low))
			return false;
		*p++ = (high << 4) | low;
	}
	return true;
}

void dynbuf_init(struct dynbuf *buf)
{
	dynbuf_init_mem(buf, NULL, 0, true);
}

void dynbuf_init_mem(struct dynbuf *buf, void *ptr, size_t size, bool owned)
{
	buf->ptr = ptr;
	buf->size = size;
	buf->cap = size;
	buf->off = 0;
	buf->owned = owned;
}

void *dynbuf_write(struct dynbuf *buf, size_t size)
{
	size_t end = buf->off + size;
	if (end < buf->off) {
		fprintf(stderr, "dynbuf_write: size overflow\n");
		return NULL;
	}

	if (end > buf->cap) {
		if (!buf->owned)
			return false;
		size_t new_cap = buf->cap * 2;
		if (new_cap < end)
			new_cap = end;
		void *ptr = realloc(buf->ptr, new_cap);
		if (!ptr) {
			perror("realloc");
			return NULL;
		}
		buf->ptr = ptr;
	}

	void *p = (char *)buf->ptr + buf->off;
	buf->size += size;
	buf->off += size;

	return p;
}

const void *dynbuf_read(struct dynbuf *buf, size_t size)
{
	size_t end = buf->off + size;
	if (end < buf->off || end > buf->size) {
		fprintf(stderr, "dynbuf_read: buffer too small\n");
		return NULL;
	}

	const void *p = (char *)buf->ptr + buf->off;
	buf->off += size;

	return p;
}

bool dynbuf_write_data(struct dynbuf *buf, const void *src, size_t size)
{
	void *ptr = dynbuf_write(buf, size);
	if (!ptr)
		return false;
	memcpy(ptr, src, size);
	return true;
}

bool dynbuf_read_data(struct dynbuf *buf, void *dst, size_t size)
{
	const void *ptr = dynbuf_read(buf, size);
	if (!ptr)
		return false;
	memcpy(dst, ptr, size);
	return true;
}

void *dynbuf_release(struct dynbuf *buf)
{
	if (!buf)
		return NULL;
	void *ptr = buf->ptr;
	buf->ptr = NULL;
	buf->size = 0;
	buf->cap = 0;
	buf->off = 0;
	return ptr;
}

void dynbuf_reset(struct dynbuf *buf)
{
	if (!buf)
		return;
	bool owned = buf->owned;
	void *ptr = dynbuf_release(buf);
	if (owned)
		free(ptr);
}
