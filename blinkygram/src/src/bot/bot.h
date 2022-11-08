#ifndef BOT_H
#define BOT_H

#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>

#include "client.h"
#include "crypto.h"
#include "protocol.h"

/* A chat message. */
struct bot_chat_msg {
	/* Message content. */
	char *content;
	/* Sender user ID. */
	uint64_t sender;
	/* Message timestamp. */
	uint64_t timestamp;
};

struct bot;

/**
 * Callback invoked when a chat message is received.
 * Returns true on success, false otherwise.
 */
typedef bool (*bot_chat_callback)(struct bot *bot,
                                  const struct bot_chat_msg *msg);

/**
 * Callback invoked when an error occurs, before stopping the bot.
 */
typedef void (*bot_error_callback)(struct bot *bot);

/* A bot. */
struct bot {
	/* Connected client. */
	struct client *client;
	/* Username. */
	const char *username;
	/* Password. */
	const char *password;
	/* Crypto key. */
	const struct crypto_key *key;
	/* Authentication token. */
	struct proto_auth_token *token;
	/* Chat callback. */
	bot_chat_callback chat_cb;
	/* Error callback. */
	bot_error_callback error_cb;
	/* Main thread. */
	pthread_t th_main;
	/* Keepalive thread. */
	pthread_t th_keepalive;
	/* Running flag. */
	atomic_bool running;
	/* Running condition variable. */
	pthread_cond_t cv_running;
	/* Running condition variable mutex. */
	pthread_mutex_t lock_running;
};

/**
 * Initializes |bot| with credentials |username| and |password| and crypto key
 * |key|, over the already-connected |client|.
 * Whenever a new chat message is received, |chat_cb| will be invoked.
 * Whenever an internal error is encountered, |error_cb| will be invoked and
 * the bot will be stopped.
 * Returns true on success, false otherwise.
 */
bool bot_init(struct bot *bot, struct client *client, const char *username,
              const char *password, const struct crypto_key *key,
              bot_chat_callback chat_cb, bot_error_callback error_cb);

/**
 * Runs |bot| in the background.
 * Returns true on success, false otherwise.
 */
bool bot_start(struct bot *bot);

/**
 * Initiates termination of |bot|.
 * Returns true on success, false otherwise.
 */
bool bot_stop(struct bot *bot);

/**
 * Wait for |bot| to terminate.
 * Return true on success, false otherwise.
 */
bool bot_join(const struct bot *bot);

#endif
