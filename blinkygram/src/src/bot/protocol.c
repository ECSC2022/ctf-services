#include "protocol.h"

#include <stdatomic.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "util.h"

/* Next sequence number. */
static atomic_uint g_next_seq;

void *protocol_request(int fd, enum proto_req_kind kind, const void *req_buf,
                       size_t req_size, enum proto_reply_status *status,
                       size_t *reply_size)
{
	char *reply_data = NULL;

	uint32_t seq = atomic_fetch_add(&g_next_seq, 1);
	struct proto_msg_request req = {
	    .hdr =
	        {
	            .seq = seq,
	            .length = sizeof(req) - sizeof(req.hdr) + req_size,
	        },
	    .kind = kind,
	};

	if (!write_exactly(fd, &req, sizeof(req)))
		goto fail;
	if (!write_exactly(fd, req_buf, req_size))
		goto fail;

	struct proto_msg_reply reply;
	if (!read_exactly(fd, &reply, sizeof(reply)))
		goto fail;

	if (reply.hdr.seq != seq) {
		fprintf(stderr, "protocol_request: wrong sequence number\n");
		goto fail;
	}

	if (reply.hdr.length > MAX_MESSAGE_LEN) {
		fprintf(stderr, "protocol_request: message too large\n");
		goto fail;
	}

	size_t data_len = reply.hdr.length - (sizeof(reply) - sizeof(reply.hdr));
	if (data_len >= reply.hdr.length) {
		fprintf(stderr, "protocol_request: invalid reply length\n");
		goto fail;
	}

	reply_data = malloc(data_len + 1);
	if (!reply_data) {
		perror("malloc");
		goto fail;
	}

	if (!read_exactly(fd, reply_data, data_len))
		goto fail;
	reply_data[data_len] = '\0';

	switch (reply.status) {
	case REPLY_STATUS_OK:
	case REPLY_STATUS_FAIL:
		break;
	default:
		fprintf(stderr, "protocol_request: invalid status\n");
		goto fail;
	}

	*status = reply.status;
	*reply_size = data_len;
	return reply_data;

fail:
	free(reply_data);
	return NULL;
}

const void *protocol_read_bytes(struct dynbuf *buf, size_t *size)
{
	uint32_t length;
	if (!dynbuf_read_data(buf, &length, sizeof(length)))
		return NULL;
	*size = length;
	return dynbuf_read(buf, length);
}

void *protocol_write_bytes(struct dynbuf *buf, size_t size)
{
	uint32_t length = size;
	if (!dynbuf_write_data(buf, &length, sizeof(length)))
		return NULL;
	return dynbuf_write(buf, size);
}

char *protocol_read_string(struct dynbuf *buf)
{
	size_t len;
	const void *bytes = protocol_read_bytes(buf, &len);
	if (!bytes)
		return NULL;

	char *str = malloc(len + 1);
	if (!str)
		return NULL;

	memcpy(str, bytes, len);
	str[len] = '\0';

	return str;
}

bool protocol_write_string(struct dynbuf *buf, const char *str)
{
	size_t len = strlen(str);
	void *bytes = protocol_write_bytes(buf, len);
	if (!bytes)
		return false;
	memcpy(bytes, str, len);
	return true;
}
