#ifndef CHAT_H
#define CHAT_H

#include <stdbool.h>

#include "bot.h"

/**
 * A bot_chat_callback that implements the bot's logic.
 */
bool chat_callback(struct bot *bot, const struct bot_chat_msg *msg);

#endif
