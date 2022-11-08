#include "storage.h"

#include <dirent.h>
#include <errno.h>
#include <inttypes.h>
#include <linux/limits.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "protocol.h"
#include "storage.h"
#include "util.h"

/* Next item ID. */
static uint64_t g_next_item_id;

/* Storage lock. */
static pthread_mutex_t g_storage_lock;

#define LOCK()                                                                 \
	do {                                                                       \
		if (pthread_mutex_lock(&g_storage_lock)) {                             \
			fprintf(stderr, "%s: failed to lock storage mutex\n", __func__);   \
			return false;                                                      \
		}                                                                      \
	} while (0)
#define UNLOCK()                                                               \
	do {                                                                       \
		if (pthread_mutex_unlock(&g_storage_lock)) {                           \
			fprintf(stderr, "%s: failed to unlock storage mutex\n", __func__); \
			return false;                                                      \
		}                                                                      \
	} while (0)

struct item_data {
	uint64_t seller;
	uint64_t price;
	uint64_t currency;
	char content[];
};

bool storage_init(void)
{
	bool ret = false;
	DIR *dir = NULL;

	if (pthread_mutex_init(&g_storage_lock, NULL)) {
		fprintf(stderr, "storage_init: failed to init lock\n");
		goto cleanup;
	}

	if (mkdir(STORAGE_PATH, 0777) == -1 && errno != EEXIST) {
		perror("mkdir");
		goto cleanup;
	}

	if (mkdir(ITEMS_PATH, 0777) == -1 && errno != EEXIST) {
		perror("mkdir");
		goto cleanup;
	}

	dir = opendir(ITEMS_PATH);
	if (!dir) {
		perror("opendir");
		goto cleanup;
	}

	errno = 0;
	struct dirent *entry;
	while (1) {
		errno = 0;
		entry = readdir(dir);
		if (!entry) {
			if (errno) {
				perror("readdir");
				goto cleanup;
			}
			break;
		}

		uint64_t id;
		if (!strtoul_checked(entry->d_name, 10, &id))
			continue;
		if (id >= g_next_item_id)
			g_next_item_id = id + 1;
	}

	ret = true;

cleanup:
	if (dir)
		closedir(dir);
	return ret;
}

bool storage_item_new(uint64_t seller, uint64_t price, uint64_t currency,
                      const char *content, uint64_t *id)
{
	LOCK();

	bool ret = false;

	char buf[sizeof(struct item_data) + MAX_ITEM_LEN];
	struct item_data *data = (void *)buf;

	size_t content_len = strlen(content);
	if (content_len > MAX_ITEM_LEN)
		content_len = MAX_ITEM_LEN;

	data->seller = seller;
	data->price = price;
	data->currency = currency;
	memcpy(data->content, content, content_len);

	*id = g_next_item_id++;

	char path[PATH_MAX];
	snprintf(path, sizeof(path), ITEMS_PATH "/%" PRIu64, *id);
	if (!write_file(path, data, sizeof(*data) + content_len))
		goto cleanup;

	snprintf(path, sizeof(path), ITEMS_PATH "/%" PRIu64 ".receipts", *id);
	if (!write_file(path, "", 0))
		goto cleanup;

	ret = true;

cleanup:
	UNLOCK();
	return ret;
}

bool storage_item_load(struct storage_item *item, uint64_t id)
{
	LOCK();

	bool ret = false;

	item->id = id;

	size_t size;
	char path[PATH_MAX];
	snprintf(path, sizeof(path), ITEMS_PATH "/%" PRIu64, id);
	void *buf = read_file(path, &size);
	if (!buf)
		goto cleanup;
	if (size < sizeof(struct item_data) ||
	    size > sizeof(struct item_data) + MAX_ITEM_LEN) {
		fprintf(stderr, "storage_item_load: corrupted item\n");
		free(buf);
		goto cleanup;
	}

	struct item_data *data = buf;
	item->seller = data->seller;
	item->price = data->price;
	item->currency = data->currency;
	size_t content_len = size - sizeof(struct item_data);
	memcpy(item->content, data->content, content_len);
	item->content[content_len] = '\0';
	free(buf);

	snprintf(path, sizeof(path), ITEMS_PATH "/%" PRIu64 ".receipts", id);
	buf = read_file(path, &size);
	if (!buf)
		goto cleanup;
	if (size % sizeof(struct proto_transfer_receipt)) {
		fprintf(stderr, "storage_item_load: corrupted receipts\n");
		free(buf);
		goto cleanup;
	}

	item->num_receipts = size / sizeof(struct proto_transfer_receipt);
	item->receipts = buf;

	ret = true;

cleanup:
	UNLOCK();
	return ret;
}

bool storage_item_add_receipt(uint64_t id,
                              const struct proto_transfer_receipt *receipt)
{
	LOCK();

	bool ret = false;
	FILE *fp = NULL;

	char path[PATH_MAX];
	snprintf(path, sizeof(path), ITEMS_PATH "/%" PRIu64 ".receipts", id);

	fp = fopen(path, "a");
	if (!fp) {
		perror("fopen");
		goto cleanup;
	}

	if (fwrite(receipt, sizeof(*receipt), 1, fp) != 1) {
		perror("fwrite");
		goto cleanup;
	}

	ret = true;

cleanup:
	if (fp)
		fclose(fp);
	UNLOCK();
	return ret;
}

void storage_item_free(struct storage_item *item)
{
	free(item->receipts);
}
