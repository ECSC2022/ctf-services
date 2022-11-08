#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/random.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "bot.h"
#include "chat.h"
#include "client.h"
#include "crypto.h"
#include "protocol.h"
#include "storage.h"

#define USERNAME "marketbot"
#define PASSWORD_LEN 16

static struct bot *g_bots;
static size_t g_bots_count;

static atomic_int g_exit_status;

static void term_handler(int signum)
{
	(void)signum;
	printf("Terminating...\n");
	fflush(stdout);
	for (size_t i = 0; i < g_bots_count; i++)
		bot_stop(&g_bots[i]);
}

static void error_callback(struct bot *bot)
{
	(void)bot;
	if (atomic_load(&g_exit_status))
		return;
	atomic_store(&g_exit_status, EXIT_FAILURE);
	fprintf(stderr, "Error occurred, terminating...\n");
	for (size_t i = 0; i < g_bots_count; i++)
		bot_stop(&g_bots[i]);
}

static char *get_password(void)
{
	if (access(PASSWORD_PATH, F_OK) == -1) {
		char buf[PASSWORD_LEN + 1];
		if (!rand_alnum(buf, PASSWORD_LEN))
			exit(EXIT_FAILURE);
		if (!write_file(PASSWORD_PATH, buf, PASSWORD_LEN))
			exit(EXIT_FAILURE);
	}

	char *password = read_file(PASSWORD_PATH, NULL);
	if (!password)
		exit(EXIT_FAILURE);

	return password;
}

int main()
{
	if (!storage_init())
		exit(EXIT_FAILURE);

	const char *host = getenv("BOT_SERVER_HOST");
	if (!host || *host == '\0') {
		fprintf(stderr, "Error: BOT_SERVER_HOST not set\n");
		exit(EXIT_FAILURE);
	}

	const char *s_port = getenv("BOT_SERVER_PORT");
	if (!s_port || *s_port == '\0') {
		fprintf(stderr, "Error: BOT_SERVER_PORT not set\n");
		exit(EXIT_FAILURE);
	}
	uint16_t port = atoi(s_port);

	const char *s_workers = getenv("BOT_WORKERS");
	if (!s_workers || *s_workers == '\0') {
		fprintf(stderr, "Error: BOT_WORKERS not set\n");
		exit(EXIT_FAILURE);
	}
	size_t workers = atoi(s_workers);

	printf("Starting up with %zu workers\n", workers);
	fflush(stdout);

	char *password = get_password();

	struct crypto_key key;
	if (!crypto_key_import(&key, KEY_PATH))
		exit(EXIT_FAILURE);

	g_bots = calloc(workers, sizeof(struct bot));
	g_bots_count = workers;

	struct client *clients = calloc(workers, sizeof(struct client));

	for (size_t i = 0; i < workers; i++) {
		if (!client_init(&clients[i]))
			exit(EXIT_FAILURE);
		if (!client_connect(&clients[i], host, port))
			exit(EXIT_FAILURE);
		if (!bot_init(&g_bots[i], &clients[i], USERNAME, password, &key,
		              chat_callback, error_callback))
			exit(EXIT_FAILURE);
	}

	for (size_t i = 0; i < workers; i++) {
		if (!bot_start(&g_bots[i]))
			exit(EXIT_FAILURE);
	}

	printf("Startup complete.\n");
	fflush(stdout);

	signal(SIGINT, term_handler);
	signal(SIGTERM, term_handler);

	for (size_t i = 0; i < workers; i++) {
		if (!bot_join(&g_bots[i]))
			exit(EXIT_FAILURE);
	}

	exit(atomic_load(&g_exit_status));
}
