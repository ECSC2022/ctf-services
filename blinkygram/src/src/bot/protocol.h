#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "crypto.h"
#include "util.h"

/* Maximum message length. */
#define MAX_MESSAGE_LEN 8192U

/* Message header. */
struct proto_msg_header {
	/* Sequence number to link a request with a reply. */
	uint32_t seq;
	/* Length of payload. */
	uint32_t length;
} __attribute__((packed));

/* Request kinds. */
enum proto_req_kind {
	REQUEST_KIND_ECHO = 0x00,
	REQUEST_KIND_REGISTER = 0x01,
	REQUEST_KIND_AUTH = 0x02,
	REQUEST_KIND_USERID = 0x03,
	REQUEST_KIND_USERNAME = 0x04,
	REQUEST_KIND_PUBKEY = 0x05,
	REQUEST_KIND_CHAT_SEND = 0x06,
	REQUEST_KIND_CHAT_READ = 0x07,
	REQUEST_KIND_BALANCE = 0x08,
	REQUEST_KIND_TRANSFER = 0x09,
	REQUEST_KIND_RECEIVE = 0x0a,
	REQUEST_KIND_MINT = 0x0b,
	REQUEST_KIND_CHECK_RECEIPT = 0x0c,
	REQUEST_KIND_NEW_BACKUP = 0x0d,
	REQUEST_KIND_GET_BACKUP = 0x0e,
};

/* Reply status codes. */
enum proto_reply_status {
	REPLY_STATUS_OK = 0x00,
	REPLY_STATUS_FAIL = 0x01,
};

/* Request message. */
struct proto_msg_request {
	/* Message header. */
	struct proto_msg_header hdr;
	/* Request kind. */
	uint8_t kind;
} __attribute__((packed));

/* Reply message. */
struct proto_msg_reply {
	/* Message header. */
	struct proto_msg_header hdr;
	/* Status code. */
	uint8_t status;
} __attribute__((packed));

/* An authentication token. */
struct proto_auth_token {
	/* User ID. */
	uint64_t userid;
	/* Server signature. */
	char sig[CRYPTO_SIG_SIZE];
} __attribute__((packed));

/* A transfer receipt. */
struct proto_transfer_receipt {
	/* Amount. */
	uint64_t amount;
	/* Currency. */
	uint64_t currency;
	/* Recipient user ID. */
	uint64_t recipient;
	/* Server signature. */
	char sig[CRYPTO_SIG_SIZE];
} __attribute__((packed));

/**
 * Sends the request of kind |kind| with data in |req_buf| of size |req_size|.
 * On success, returns a pointer to a buffer containing the reply, and stores
 * the reply status in |status| and the reply size in |reply_size|. The reply
 * buffer is owned by the caller, which should free() it when no longer needed.
 * The reply is NUL-terminated (terminator not included in |reply_size|).
 * On failure, returns NULL and the contents of |status| and |reply_size| are
 * undefined.
 */
void *protocol_request(int fd, enum proto_req_kind kind, const void *req_buf,
                       size_t req_size, enum proto_reply_status *status,
                       size_t *reply_size);

/**
 * Reads a bytes field from |buf|.
 * On success, returns a pointer to the bytes and stores the length in |size|.
 * On failure, returns NULL and the contents of |size| are undefined.
 */
const void *protocol_read_bytes(struct dynbuf *buf, size_t *size);

/**
 * Writes a bytes field of size |size| to |buf|.
 * On success, returns a pointer to the bytes.
 * On failure, returns NULL.
 */
void *protocol_write_bytes(struct dynbuf *buf, size_t size);

/**
 * Reads a string from |buf|.
 * On success, returns a pointer to a string, to be free()'d by the caller.
 * On failure, returns NULL.
 */
char *protocol_read_string(struct dynbuf *buf);

/**
 * Writes the string |str| to |buf|.
 * Returns true on success, false otherwise.
 */
bool protocol_write_string(struct dynbuf *buf, const char *str);

#endif
