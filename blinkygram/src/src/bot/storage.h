#ifndef STORAGE_H
#define STORAGE_H

#include <stdbool.h>

#include "protocol.h"

/* Path to storage. */
#define STORAGE_PATH "./storage"

/* Path to password file. */
#define PASSWORD_PATH STORAGE_PATH "/password"
/* Path to key file. */
#define KEY_PATH STORAGE_PATH "/key.pem"
/* Path to items directory. */
#define ITEMS_PATH STORAGE_PATH "/items"

/* Maximum item length. */
#define MAX_ITEM_LEN 100

struct storage_item {
	/* Item content. */
	char content[MAX_ITEM_LEN + 1];
	/* Item ID. */
	uint64_t id;
	/* Seller user ID. */
	uint64_t seller;
	/* Price. */
	uint64_t price;
	/* Currency ID. */
	uint64_t currency;
	/* Number of seller transfer receipts. */
	size_t num_receipts;
	/* Array of seller transfer receipts. */
	struct proto_transfer_receipt *receipts;
};

/**
 * Initializes the storage.
 */
bool storage_init(void);

/**
 * Creates a new item, sold by user ID |seller| at |price| |curency|, with
 * content |content|.
 * On success, returns true and stores the new item's ID in |id|.
 * On failure, returns false and |id| is undefined.
 */
bool storage_item_new(uint64_t seller, uint64_t price, uint64_t currency,
                      const char *content, uint64_t *id);

/**
 * Loads the item with ID |id| into |item|.
 * Returns true on success, false otherwise.
 */
bool storage_item_load(struct storage_item *item, uint64_t id);

/**
 * Adds |receipt| to the item with ID |id|.
 * Returns true on success, false otherwise.
 */
bool storage_item_add_receipt(uint64_t id,
                              const struct proto_transfer_receipt *receipt);

/**
 * Frees memory used by |item|.
 */
void storage_item_free(struct storage_item *item);

#endif
