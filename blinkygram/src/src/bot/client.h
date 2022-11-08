#ifndef CLIENT_H
#define CLIENT_H

#include "util.h"
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>

/* A client. */
struct client {
	/* Client lock. */
	pthread_mutex_t lock;
	/* Socket descriptor. */
	int fd;
};

/**
 * Initializes |client|.
 * Returns true on success, false otherwise.
 */
bool client_init(struct client *client);

/**
 * Connects |client| to |host| on TCP port |port|.
 * Returns true on success, false otherwise.
 */
bool client_connect(struct client *client, const char *host, uint16_t port);

/**
 * Sends an echo request with payload |buf| of size |size| and checks the reply.
 * Returns true on success, false otherwise.
 */
bool client_echo(struct client *client, void *buf, size_t size);

/**
 * Registers a user with credentials |username| and |password| and public key
 * |pubkey|. If |exist_ok| is true, registering an existing user is not
 * considered an error.
 * Returns true on success, false otherwise.
 */
bool client_register(struct client *client, const char *username,
                     const char *password, const char *pubkey, bool exist_ok);

/**
 * Authenticates a user with credentials |username| and |password|.
 * On success, returns the authentication token, to be free()'d by the caller.
 * On failure, returns NULL.
 */
struct proto_auth_token *
client_auth(struct client *client, const char *username, const char *password);

/**
 * Gets a user's ID from their username.
 * On success, returns true and stores the user ID in |userid|.
 * On failure, returns false and |userid| is undefined.
 */
bool client_get_userid(struct client *client,
                       const struct proto_auth_token *token,
                       const char *username, uint64_t *userid);

/**
 * Gets a user's username from their user ID.
 * On success, returns the username, which should be free()'d by the caller.
 * On failure, returns NULL.
 */
char *client_get_username(struct client *client,
                          const struct proto_auth_token *token,
                          uint64_t userid);

/**
 * Gets a user's pubkey from their user ID.
 * On success, returns the pubkey, which should be free()'d by the caller.
 * On failure, returns NULL.
 */
char *client_get_pubkey(struct client *client,
                        const struct proto_auth_token *token, uint64_t userid);

/**
 * Sends a chat message with content |content| to the user with ID |userid|.
 * Returns true on success, false otherwise.
 */
bool client_chat_send(struct client *client,
                      const struct proto_auth_token *token, uint64_t userid,
                      const char *content);

/**
 * Reads an unread message.
 * Returns true on success, false otherwise.
 * When successful with a message available to be read, |content|, |sender|,
 * and |timestamp| are respectively populated with a pointer to the content,
 * to be free()'d by the caller, the sender user ID and the timestamp.
 * When successful with no messages available, |content| is set to NULL.
 */
bool client_chat_read(struct client *client,
                      const struct proto_auth_token *token, char **content,
                      uint64_t *sender, uint64_t *timestamp);

/**
 * Retrieves the user's balance for |currency|.
 * On success, returns true and stores the balance in |balance|.
 * On failure, returns false and |balance| is undefined.
 */
bool client_get_balance(struct client *client,
                        const struct proto_auth_token *token, uint64_t currency,
                        uint64_t *balance);

/**
 * Transfers |amount| of |currency| to the user with ID |userid|.
 * On success, returns the transfer receipt, to be free()'d by the caller.
 * On failure, returns NULL.
 */
struct proto_transfer_receipt *
client_transfer(struct client *client, const struct proto_auth_token *token,
                uint64_t amount, uint64_t currency, uint64_t userid);

/**
 * Receives the transfer for |receipt|.
 * Returns true on success, false on failure.
 */
bool client_receive(struct client *client, const struct proto_auth_token *token,
                    const struct proto_transfer_receipt *receipt);

/**
 * Checks whether |receipt| is valid.
 * On success, returns true and |valid| indicates whether the receipt is valid.
 * On failure, returns false and |valid| is undefined.
 */
bool client_check_receipt(struct client *client,
                          const struct proto_auth_token *token,
                          const struct proto_transfer_receipt *receipt,
                          bool *valid);

/**
 * Mints |amount| of a new currency.
 * On success, returns true and store the new currency ID in |currency|.
 * On failure, returns false and |currency| is undefined.
 */
bool client_mint(struct client *client, const struct proto_auth_token *token,
                 uint64_t amount, uint64_t *currency);

/**
 * Creates a new backup.
 * On success, returns the ID of the backup, to be free()'d by the caller.
 * On failure, returns NULL.
 */
char *client_new_backup(struct client *client,
                        const struct proto_auth_token *token);

/**
 * Retrieves the backup with ID |id|.
 * On success, returns the backup content, to be free()'d by the caller, and
 * stores its size in |size|.
 * On failure, returns NULL and |size| is undefined.
 */
void *client_get_backup(struct client *client,
                        const struct proto_auth_token *token, const char *id,
                        size_t *size);

#endif
