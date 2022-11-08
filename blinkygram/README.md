Blinkygram
==========
Communities lost touch with each other. You could walk days before seeing other survivors, and even then making contact was always risky. Until one day, a treasure trove of brand new communication devices was found. Legend has it that it was a failed product on a tech giant of the old days buried deep into the mountains to avoid a new round of bad press.

Blinkygram is a messaging app with a focus on speed and security. It's super-fast, simple, and free. You can use Blinkygram on all your devices simultaneously — but don't expect it to work correctly. Blinkygram has over 300 monthly active users and is one of the 10 messaging apps still operational worldwide.

With Blinkygram, you can send messages, text, and more text. You can find people by their usernames. As a result, Blinkygram is like SMS, if you still remember what those are — and can take care of all your business and survival messaging needs. In addition, Blinkygram supports verified payments, meme currencies, as well as secure backups.


Directory structure
-------------------
- `checkers/`: checkers.
- **`dist/`: deployable directory, to be given to teams.**
- `exploits/`: exploits.
- `src/`: sources.


Vulnerabilities
---------------

### (1) Backup flagstore: path traversal in get backup

**Description:** In `server/handlers.py`, `get_backup_handler` is vulnerable to a path traversal through the `req.id`, allowing to leak other users' backups.

**Patch:** Input sanitization.

### (2) Backup flagstore: ZIP symbolic links

**Description:** In `server/handlers.py`, `new_backup_handler` uses the `unzip` CLI command to unzip the backup. It is possible to store a symlink to other users' backup files to steal flags, or to the source code to steal patches.

**Patch:** Avoid `unzip` or clean up symlinks.

### (3) Market flagstore: negative amount in transfers

**Description:** In `server/protocol.py`, the `amount` field of `TransferRequest` is signed, which allows bypassing the `if req.amount > balance.balance` check in `transfer_handler` in `server/handlers.py`, allowing to create money. The money can then be used to buy flags from the market. The field is signed in `TransferReceipt`, too, but that is not an exploitable issue in and of itself.

**Patch:** Make the `amount` field `Uint64` in `TransferRequest` and `TransferReceipt`.

### (4) Market flagstore: ECDSA malleability

**Description:** Transfer receipts are checked using the `python-ecdsa` library, which is vulnerable to ECDSA malleability. This allows to double-spend transfer, and therefore create money exponentially fast starting from the small initial balance. The money can then be used to buy flags from the market.

**Patch:** ensure `s` is in the low (or high) half of the field on signing and verification.

### (5) Market flagstore: static ECDSA nonce

**Description:** In `bot/crypto.c`, `crypto_key_sign` generates a static ECDSA nonce. By obtaining multiple signatures via view tokens, one can recover the bot's private key and craft arbitrary view tokens to read flags.

**Patch:** Pass `NULL` as `kinv` and `rp` to `ECDSA_do_sign_ex` and reset the private key.

### (6) Market flagstore: OOB read in item buy

**Description:** In `bot/chat.c`, `handle_buy` does not check bounds when comparing known characters for applying the discount. One can specify positions landing in predictable memory to obtain a full discount and get the flag for free.

**Patch:** Bound checking (easier to hack it inside the server).


Known bugs
----------

- The market bot does not remember used receipts, so the same transfer receipt can be used to buy multiple items in the same currency from the same seller (or the same item multiple times) before the seller spends it. This is not an issue as every flag has a different seller.

- There is a potential race between the market bot checking a transfer receipt and that receipt being spent, so the same receipt could be used to buy multiple items in the same currency from the same seller (or the same item multiple times). This is not an issue as every flag has a different seller.

- There is a potential race between minting and operations that can initialize the user's balance. A user that guesses the incremental new currency ID could transfer the initial amount after the currency is created but before the mint balance is set, thereby creating more money than minted. Since minting already allows to create an arbitrary amount of money, this has no impact.

- There is a potential race when initializing a user's balance, as the server first fetches the balance row and, if it does not exist, sets the initial balance. A user could perform another initializing operation and transfer out the initial balance after the fetch but before the initialization, thereby creating an amount of money equal to the initial balance. Since such an amount can be obtained by simply registering a new user, this has no impact.
