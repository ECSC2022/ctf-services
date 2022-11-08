#define _POSIX_C_SOURCE 200112L /* addrinfo */

#include "client.h"

#include <netdb.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>
#include <unistd.h>

#include "protocol.h"
#include "util.h"

/* Socket send/receive timeout, in seconds. */
#define SOCKET_TIMEOUT 10

#define LOCK()                                                                 \
	do {                                                                       \
		pthread_mutex_lock(&client->lock);                                     \
	} while (0)
#define UNLOCK()                                                               \
	do {                                                                       \
		pthread_mutex_unlock(&client->lock);                                   \
	} while (0)

static void reply_error(void *reply, size_t size)
{
	fprintf(stderr, "failure reply: ");
	fwrite(reply, 1, size, stderr);
	fprintf(stderr, "\n");
}

static bool request(const struct client *client, enum proto_req_kind kind,
                    const struct dynbuf *req_buf, struct dynbuf *reply_buf,
                    enum proto_reply_status *status, bool check_status)
{
	size_t reply_size;
	enum proto_reply_status l_status;
	void *reply = protocol_request(client->fd, kind, req_buf->ptr,
	                               req_buf->size, &l_status, &reply_size);
	if (!reply)
		return false;

	if (check_status && l_status == REPLY_STATUS_FAIL) {
		reply_error(reply, reply_size);
		free(reply);
		return false;
	}

	if (reply_buf)
		dynbuf_init_mem(reply_buf, reply, reply_size, true);
	else
		free(reply);

	if (status)
		*status = l_status;

	return true;
}

bool client_init(struct client *client)
{
	if (pthread_mutex_init(&client->lock, NULL)) {
		fprintf(stderr, "client_init: failed to init lock\n");
		return false;
	}
	client->fd = -1;
	return true;
}

bool client_connect(struct client *client, const char *host, uint16_t port)
{
	LOCK();

	struct addrinfo *addr = NULL;
	int fd = -1;
	bool ret = false;

	addr = resolve_host(host, port);
	if (!addr)
		goto cleanup;

	fd = socket(addr->ai_family, addr->ai_socktype, addr->ai_protocol);
	if (fd == -1) {
		perror("socket");
		goto cleanup;
	}

	struct timeval tv;
	tv.tv_sec = SOCKET_TIMEOUT;
	tv.tv_usec = 0;
	if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)) == -1) {
		perror("setsockopt(SO_RCVTIMEO)");
		goto cleanup;
	}
	if (setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv)) == -1) {
		perror("setsockopt(SO_SNDTIMEO)");
		goto cleanup;
	}

	if (connect(fd, addr->ai_addr, addr->ai_addrlen) == -1) {
		perror("connect");
		goto cleanup;
	}

	client->fd = fd;

	ret = true;

cleanup:
	if (addr)
		freeaddrinfo(addr);
	if (fd != -1 && !ret)
		close(fd);
	UNLOCK();
	return ret;
}

bool client_echo(struct client *client, void *buf, size_t size)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init_mem(&req, buf, size, false);
	dynbuf_init(&reply);

	if (!request(client, REQUEST_KIND_ECHO, &req, &reply, NULL, true))
		goto cleanup;

	if (reply.size != size || memcmp(reply.ptr, buf, size)) {
		fprintf(stderr, "client_echo: mismatched payload\n");
		goto cleanup;
	}

	ret = true;

cleanup:
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

bool client_register(struct client *client, const char *username,
                     const char *password, const char *pubkey, bool exist_ok)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!protocol_write_string(&req, username))
		goto cleanup;
	if (!protocol_write_string(&req, password))
		goto cleanup;
	if (!protocol_write_string(&req, pubkey))
		goto cleanup;

	enum proto_reply_status status;
	if (!request(client, REQUEST_KIND_REGISTER, &req, &reply, &status,
	             !exist_ok))
		goto cleanup;

	if (status == REPLY_STATUS_FAIL && strcmp(reply.ptr, "User exists")) {
		reply_error(reply.ptr, reply.size);
		goto cleanup;
	}

	ret = true;

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

struct proto_auth_token *client_auth(struct client *client,
                                     const char *username, const char *password)
{
	LOCK();

	struct proto_auth_token *token = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!protocol_write_string(&req, username))
		goto cleanup;
	if (!protocol_write_string(&req, password))
		goto cleanup;

	if (!request(client, REQUEST_KIND_AUTH, &req, &reply, NULL, true))
		goto cleanup;

	if (reply.size != sizeof(*token)) {
		fprintf(stderr, "client_auth: invalid reply size\n");
		goto cleanup;
	}

	token = dynbuf_release(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return token;
}

bool client_get_userid(struct client *client,
                       const struct proto_auth_token *token,
                       const char *username, uint64_t *userid)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!protocol_write_string(&req, username))
		goto cleanup;

	if (!request(client, REQUEST_KIND_USERID, &req, &reply, NULL, true))
		goto cleanup;

	if (reply.size != sizeof(uint64_t)) {
		fprintf(stderr, "client_get_userid: invalid reply size\n");
		goto cleanup;
	}

	*userid = *(uint64_t *)reply.ptr;
	ret = true;

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

char *client_get_username(struct client *client,
                          const struct proto_auth_token *token, uint64_t userid)
{
	LOCK();

	char *username = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &userid, sizeof(userid)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_USERNAME, &req, &reply, NULL, true))
		goto cleanup;

	username = protocol_read_string(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return username;
}

char *client_get_pubkey(struct client *client,
                        const struct proto_auth_token *token, uint64_t userid)
{
	LOCK();

	char *pubkey = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &userid, sizeof(userid)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_PUBKEY, &req, &reply, NULL, true))
		goto cleanup;

	pubkey = protocol_read_string(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return pubkey;
}

bool client_chat_send(struct client *client,
                      const struct proto_auth_token *token, uint64_t userid,
                      const char *content)
{
	LOCK();

	bool ret = false;

	struct dynbuf req;
	dynbuf_init(&req);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &userid, sizeof(userid)))
		goto cleanup;
	if (!protocol_write_string(&req, content))
		goto cleanup;

	if (!request(client, REQUEST_KIND_CHAT_SEND, &req, NULL, NULL, true))
		goto cleanup;

	ret = true;

cleanup:
	dynbuf_reset(&req);
	UNLOCK();
	return ret;
}

bool client_chat_read(struct client *client,
                      const struct proto_auth_token *token, char **content,
                      uint64_t *sender, uint64_t *timestamp)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;

	enum proto_reply_status status;
	if (!request(client, REQUEST_KIND_CHAT_READ, &req, &reply, &status, false))
		goto cleanup;

	if (status == REPLY_STATUS_FAIL) {
		if (!strcmp(reply.ptr, "No messages")) {
			ret = true;
			*content = NULL;
		} else {
			reply_error(reply.ptr, reply.size);
		}
		goto cleanup;
	}

	if (!dynbuf_read_data(&reply, sender, sizeof(*sender)))
		goto cleanup;
	if (!dynbuf_read_data(&reply, timestamp, sizeof(*timestamp)))
		goto cleanup;
	*content = protocol_read_string(&reply);
	if (!*content)
		goto cleanup;

	ret = true;

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

bool client_get_balance(struct client *client,
                        const struct proto_auth_token *token, uint64_t currency,
                        uint64_t *balance)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &currency, sizeof(currency)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_BALANCE, &req, &reply, NULL, true))
		goto cleanup;

	if (!dynbuf_read_data(&reply, balance, sizeof(*balance)))
		goto cleanup;

	ret = true;

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

struct proto_transfer_receipt *
client_transfer(struct client *client, const struct proto_auth_token *token,
                uint64_t amount, uint64_t currency, uint64_t userid)
{
	LOCK();

	struct proto_transfer_receipt *receipt = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &amount, sizeof(amount)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &currency, sizeof(currency)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &userid, sizeof(userid)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_TRANSFER, &req, &reply, NULL, true))
		goto cleanup;

	if (reply.size != sizeof(*receipt)) {
		fprintf(stderr, "client_transfer: invalid reply size\n");
		goto cleanup;
	}

	receipt = dynbuf_release(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return receipt;
}

bool client_receive(struct client *client, const struct proto_auth_token *token,
                    const struct proto_transfer_receipt *receipt)
{
	LOCK();

	bool ret = false;

	struct dynbuf req;
	dynbuf_init(&req);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, receipt, sizeof(*receipt)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_RECEIVE, &req, NULL, NULL, true))
		goto cleanup;

	ret = true;

cleanup:
	dynbuf_reset(&req);
	UNLOCK();
	return ret;
}

bool client_mint(struct client *client, const struct proto_auth_token *token,
                 uint64_t amount, uint64_t *currency)
{
	LOCK();

	bool ret = false;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, &amount, sizeof(amount)))
		goto cleanup;

	if (!request(client, REQUEST_KIND_MINT, &req, &reply, NULL, true))
		goto cleanup;

	if (!dynbuf_read_data(&reply, currency, sizeof(*currency)))
		goto cleanup;

	ret = true;

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return ret;
}

bool client_check_receipt(struct client *client,
                          const struct proto_auth_token *token,
                          const struct proto_transfer_receipt *receipt,
                          bool *valid)
{
	LOCK();

	bool ret = false;

	struct dynbuf req;
	dynbuf_init(&req);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!dynbuf_write_data(&req, receipt, sizeof(*receipt)))
		goto cleanup;

	enum proto_reply_status status;
	if (!request(client, REQUEST_KIND_CHECK_RECEIPT, &req, NULL, &status,
	             false))
		goto cleanup;

	ret = true;
	*valid = (status == REPLY_STATUS_OK);

cleanup:
	dynbuf_reset(&req);
	UNLOCK();
	return ret;
}

char *client_new_backup(struct client *client,
                        const struct proto_auth_token *token)
{
	LOCK();

	char *id = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!protocol_write_bytes(&req, 0))
		goto cleanup;

	if (!request(client, REQUEST_KIND_NEW_BACKUP, &req, &reply, NULL, true))
		goto cleanup;

	id = protocol_read_string(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return id;
}

void *client_get_backup(struct client *client,
                        const struct proto_auth_token *token, const char *id,
                        size_t *size)
{
	LOCK();

	void *backup = NULL;

	struct dynbuf req, reply;
	dynbuf_init(&req);
	dynbuf_init(&reply);

	if (!dynbuf_write_data(&req, token, sizeof(*token)))
		goto cleanup;
	if (!protocol_write_string(&req, id))
		goto cleanup;

	if (!request(client, REQUEST_KIND_GET_BACKUP, &req, &reply, NULL, true))
		goto cleanup;

	*size = reply.size;
	backup = dynbuf_release(&reply);

cleanup:
	dynbuf_reset(&req);
	dynbuf_reset(&reply);
	UNLOCK();
	return backup;
}
