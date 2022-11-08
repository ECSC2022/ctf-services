#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "bot.h"

#define KEEPALIVE_SLEEP 10000

#define RUNNING (atomic_load(&bot->running))

static bool bot_sleep(struct bot *bot, unsigned long ms)
{
	struct timespec ts;
	if (clock_gettime(CLOCK_REALTIME, &ts) == -1) {
		perror("clock_gettime");
		return false;
	}

	ts.tv_sec += ms / 1000;
	ts.tv_nsec += (ms % 1000) * 1000000;
	if (ts.tv_nsec >= 1000000000) {
		ts.tv_nsec -= 1000000000;
		ts.tv_sec += 1;
	}

	if (pthread_mutex_lock(&bot->lock_running)) {
		fprintf(stderr, "bot_sleep: failed to lock running CV mutex\n");
		return false;
	}

	int ret = 0;
	while (RUNNING && !ret)
		ret = pthread_cond_timedwait(&bot->cv_running, &bot->lock_running, &ts);

	if (pthread_mutex_unlock(&bot->lock_running)) {
		fprintf(stderr, "bot_sleep: failed to unlock running CV mutex\n");
		return false;
	}

	if (ret && ret != ETIMEDOUT) {
		fprintf(stderr, "bot_sleep: failed to wait on running CV\n");
		return false;
	}

	return true;
}

static void *bot_main_thread(void *ptr)
{
	struct bot *bot = ptr;

	while (RUNNING) {
		struct bot_chat_msg msg;
		if (!client_chat_read(bot->client, bot->token, &msg.content,
		                      &msg.sender, &msg.timestamp)) {
			bot->error_cb(bot);
			break;
		}

		if (!msg.content)
			continue;

		bool ret = bot->chat_cb(bot, &msg);

		free(msg.content);

		if (!ret) {
			bot->error_cb(bot);
			break;
		}
	}

	bot_stop(bot);
	return NULL;
}

static void *bot_keepalive_thread(void *ptr)
{
	struct bot *bot = ptr;

	while (RUNNING) {
		if (!client_echo(bot->client, "PING", 4)) {
			bot->error_cb(bot);
			break;
		}
		if (!bot_sleep(bot, KEEPALIVE_SLEEP)) {
			bot->error_cb(bot);
			break;
		}
	}

	bot_stop(bot);
	return NULL;
}

bool bot_init(struct bot *bot, struct client *client, const char *username,
              const char *password, const struct crypto_key *key,
              bot_chat_callback chat_cb, bot_error_callback error_cb)
{
	bot->client = client;
	bot->username = username;
	bot->password = password;
	bot->key = key;
	bot->token = NULL;
	bot->chat_cb = chat_cb;
	bot->error_cb = error_cb;
	bot->running = false;

	if (pthread_cond_init(&bot->cv_running, NULL)) {
		fprintf(stderr, "bot_init: failed to create running CV\n");
		return false;
	}

	if (pthread_mutex_init(&bot->lock_running, NULL)) {
		fprintf(stderr, "bot_init: failed to create running CV mutex\n");
		return false;
	}

	return true;
}

bool bot_start(struct bot *bot)
{
	if (!client_register(bot->client, bot->username, bot->password,
	                     bot->key->pem_pubkey, true))
		return false;

	bot->token = client_auth(bot->client, bot->username, bot->password);
	if (!bot->token)
		return false;

	atomic_store(&bot->running, true);

	if (pthread_create(&bot->th_keepalive, NULL, bot_keepalive_thread, bot)) {
		fprintf(stderr, "bot_start: failed to create keepalive thread\n");
		return false;
	}

	if (pthread_create(&bot->th_main, NULL, bot_main_thread, bot)) {
		fprintf(stderr, "bot_start: failed to create main thread\n");
		bot_stop(bot);
		return false;
	}

	return true;
}

bool bot_stop(struct bot *bot)
{
	if (pthread_mutex_lock(&bot->lock_running)) {
		fprintf(stderr, "bot_stop: failed to lock running CV mutex\n");
		return false;
	}

	atomic_store(&bot->running, false);

	int ret = pthread_cond_broadcast(&bot->cv_running);

	if (pthread_mutex_unlock(&bot->lock_running)) {
		fprintf(stderr, "bot_stop: failed to unlock running CV mutex\n");
		return false;
	}

	if (ret) {
		fprintf(stderr, "bot_stop: failed to broadcast running CV\n");
		return false;
	}

	return true;
}

bool bot_join(const struct bot *bot)
{
	if (pthread_join(bot->th_main, NULL)) {
		fprintf(stderr, "bot_join: failed to join main thread\n");
		return false;
	}

	if (pthread_join(bot->th_keepalive, NULL)) {
		fprintf(stderr, "bot_join: failed to join keepalive thread\n");
		return false;
	}

	return true;
}
