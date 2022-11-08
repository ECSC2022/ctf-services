#include "chat.h"

#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bot.h"
#include "chat.h"
#include "client.h"
#include "crypto.h"
#include "storage.h"

struct view_token {
	uint64_t id;
	char sig[CRYPTO_SIG_SIZE];
} __attribute__((packed));

static char *next_arg(char *s)
{
	if (!s)
		return NULL;

	for (; *s; s++) {
		if (*s == ' ') {
			*s = '\0';
			return s + 1;
		}
	}

	return NULL;
}

static bool make_view_token(char *out, const struct crypto_key *key,
                            uint64_t id)
{
	struct view_token token = {
	    .id = id,
	};

	const size_t data_size = offsetof(struct view_token, sig);
	if (!crypto_key_sign(key, token.sig, &token, data_size))
		return false;

	hexencode(out, &token, sizeof(token));

	return true;
}

static bool handle_help(struct bot *bot, uint64_t sender)
{
	return client_chat_send(
	    bot->client, bot->token, sender,
	    "Welcome to Market Bot! Available commands:\n"
	    "- /help: show this help.\n"
	    "- /info <ID>: show information on item <ID>.\n"
	    "- /sell <price> <currency ID> <content>: list a new item on the "
	    "market.\n"
	    "- /buy <ID> <receipt> [<pos> <char>]...: buy item <ID> with a "
	    "hex-encoded receipt for the transfer of its price to the seller. You "
	    "can get a discount if you already know part of the item: specify one "
	    "or more <pos> <char> to prove you know <char> at position <pos>.\n"
	    "- /view <token>: show item for a view token obtained through /sell "
	    "or /buy.");
}

static bool handle_info(struct bot *bot, uint64_t sender, uint64_t id)
{
	struct storage_item item;
	if (!storage_item_load(&item, id))
		return client_chat_send(bot->client, bot->token, sender,
		                        "Unknown item ID!");

	bool ret = true;

	char buf[512];
	snprintf(buf, sizeof(buf),
	         "--- Item %" PRIu64 " ---\n"
	         "Seller: %" PRIu64 "\n"
	         "Price: %" PRIu64 " (currency %" PRIu64 ")",
	         item.id, item.seller, item.price, item.currency);

	if (sender == item.seller) {
		size_t len = strlen(buf);
		snprintf(buf + len, sizeof(buf) - len, "\nSales: %zu (receipts follow)",
		         item.num_receipts);
	}

	ret = client_chat_send(bot->client, bot->token, sender, buf);
	if (!ret)
		goto cleanup;

	if (sender == item.seller) {
		for (size_t i = 0; i < item.num_receipts; i++) {
			strcpy(buf, "Sale transfer receipt: ");
			hexencode(buf + strlen(buf), &item.receipts[i],
			          sizeof(*item.receipts));
			ret = client_chat_send(bot->client, bot->token, sender, buf);
			if (!ret)
				goto cleanup;
		}
	}

cleanup:
	storage_item_free(&item);
	return ret;
}

static bool handle_sell(struct bot *bot, uint64_t sender, uint64_t price,
                        uint64_t currency, const char *content)
{
	if (strlen(content) > MAX_ITEM_LEN)
		return client_chat_send(bot->client, bot->token, sender,
		                        "Content too long!");

	uint64_t id;
	if (!storage_item_new(sender, price, currency, content, &id))
		return false;

	char token[sizeof(struct view_token) * 2 + 1];
	if (!make_view_token(token, bot->key, id))
		return false;

	char buf[64 + sizeof(token)];
	snprintf(buf, sizeof(buf), "Created item %" PRIu64 ". View token: %s", id,
	         token);
	return client_chat_send(bot->client, bot->token, sender, buf);
}

static bool handle_buy(struct bot *bot, uint64_t sender, uint64_t id,
                       struct proto_transfer_receipt *receipt, char *rest)
{
	/* Stack layout for OOB bug on positions. Reaches known_char from
	 * item.content at negative indices. Positions are chars to avoid
	 * segfaults from excessive OOB. */
	struct buy_stack_layout {
		char known_pos[MAX_ITEM_LEN];
		char known_char[MAX_ITEM_LEN];
		struct storage_item item;
	};
	struct buy_stack_layout stack;

	size_t num_known;
	for (num_known = 0; rest; num_known++) {
		char *s_pos = rest;
		char *s_char = next_arg(s_pos);
		rest = next_arg(s_char);

		unsigned long pos;
		if (!strtoul_checked(s_pos, 10, &pos))
			return client_chat_send(bot->client, bot->token, sender,
			                        "Invalid position!");

		if (!s_char)
			return client_chat_send(bot->client, bot->token, sender,
			                        "Missing character!");
		if (strlen(s_char) != 1)
			return client_chat_send(bot->client, bot->token, sender,
			                        "Invalid character!");

		stack.known_pos[num_known] = pos;
		stack.known_char[num_known] = *s_char;
	}

	for (size_t i = 0; i < num_known; i++) {
		for (size_t j = i + 1; j < num_known; j++) {
			if (stack.known_pos[i] == stack.known_pos[j])
				return client_chat_send(bot->client, bot->token, sender,
				                        "Repeated position!");
		}
	}

	if (!storage_item_load(&stack.item, id))
		return client_chat_send(bot->client, bot->token, sender,
		                        "Unknown item ID!");

	bool ret = true;

	for (size_t i = 0; i < num_known; i++) {
		/* BUG: OOB read */
		char pos = stack.known_pos[i];
		if (stack.item.content[pos] != stack.known_char[i]) {
			ret = client_chat_send(bot->client, bot->token, sender,
			                       "Wrong character!");
			goto cleanup;
		}
	}

	size_t content_len = strlen(stack.item.content);
	if (num_known > content_len)
		num_known = content_len;
	uint64_t price = stack.item.price;
	if (content_len)
		price = price * (content_len - num_known) / content_len;

	bool valid;
	ret = client_check_receipt(bot->client, bot->token, receipt, &valid);
	if (!ret)
		goto cleanup;
	valid = valid && receipt->amount >= price;
	valid = valid && receipt->currency == stack.item.currency;
	valid = valid && receipt->recipient == stack.item.seller;
	if (!valid) {
		ret = client_chat_send(bot->client, bot->token, sender,
		                       "Invalid receipt!");
		goto cleanup;
	}

	ret = storage_item_add_receipt(id, receipt);
	if (!ret)
		goto cleanup;

	char token[sizeof(struct view_token) * 2 + 1];
	ret = make_view_token(token, bot->key, id);
	if (!ret)
		goto cleanup;

	char buf[64 + sizeof(token)];
	snprintf(buf, sizeof(buf), "Bought item %" PRIu64 ". View token: %s", id,
	         token);
	ret = client_chat_send(bot->client, bot->token, sender, buf);

cleanup:
	storage_item_free(&stack.item);
	return ret;
}

static bool handle_view(struct bot *bot, uint64_t sender,
                        const struct view_token *token)
{
	bool valid;
	const size_t data_size = offsetof(struct view_token, sig);
	if (!crypto_key_verify(bot->key, token->sig, token, data_size, &valid))
		return false;
	if (!valid)
		return client_chat_send(bot->client, bot->token, sender,
		                        "Invalid view token!");

	struct storage_item item;
	if (!storage_item_load(&item, token->id))
		return client_chat_send(bot->client, bot->token, sender,
		                        "Unknown item ID!");

	char buf[48 + MAX_ITEM_LEN];
	snprintf(buf, sizeof(buf), "Item %" PRIu64 ": %s", token->id, item.content);
	return client_chat_send(bot->client, bot->token, sender, buf);
}

bool chat_callback(struct bot *bot, const struct bot_chat_msg *msg)
{
#if 0
	printf("Message from %" PRIu64 " @ %" PRIu64 ": %s\n", msg->sender,
	       msg->timestamp, msg->content);
	fflush(stdout);
#endif

	char *cmd = msg->content;
	char *arg0 = next_arg(cmd);
	char *arg1 = next_arg(arg0);
	char *rest = next_arg(arg1);

	if (!strcmp(cmd, "/help")) {
		if (arg0)
			goto unknown;
		return handle_help(bot, msg->sender);
	}

	if (!strcmp(cmd, "/info")) {
		if (!arg0 || arg1)
			goto unknown;
		uint64_t id;
		if (!strtoul_checked(arg0, 10, &id))
			goto unknown;
		return handle_info(bot, msg->sender, id);
	}

	if (!strcmp(cmd, "/sell")) {
		if (!arg0 || !arg1 || !rest)
			goto unknown;
		uint64_t price;
		if (!strtoul_checked(arg0, 10, &price))
			goto unknown;
		uint64_t currency;
		if (!strtoul_checked(arg1, 10, &currency))
			goto unknown;
		return handle_sell(bot, msg->sender, price, currency, rest);
	}

	if (!strcmp(cmd, "/buy")) {
		if (!arg0 || !arg1)
			goto unknown;
		uint64_t id;
		if (!strtoul_checked(arg0, 10, &id))
			goto unknown;
		struct proto_transfer_receipt receipt;
		if (strlen(arg1) != sizeof(receipt) * 2)
			goto unknown;
		if (!hexdecode(&receipt, arg1))
			goto unknown;
		return handle_buy(bot, msg->sender, id, &receipt, rest);
	}

	if (!strcmp(cmd, "/view")) {
		if (!arg0 || arg1)
			goto unknown;
		struct view_token token;
		if (strlen(arg0) != sizeof(token) * 2)
			goto unknown;
		if (!hexdecode(&token, arg0))
			goto unknown;
		return handle_view(bot, msg->sender, &token);
	}

unknown:
	return client_chat_send(
	    bot->client, bot->token, msg->sender,
	    "I couldn't understand you! Try /help for a list of commands.");
}
