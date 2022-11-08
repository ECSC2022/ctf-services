#ifndef CRYPTO_H
#define CRYPTO_H

#include <openssl/ec.h>
#include <stdbool.h>

/* Size of a signature. */
#define CRYPTO_SIG_SIZE 64

/* EC key. */
struct crypto_key {
	/* PEM private key. */
	const char *pem_privkey;
	/* PEM public key. */
	const char *pem_pubkey;
	/* OpenSSL key. */
	EC_KEY *ec_key;
};

/**
 * Imports an EC private key in PEM format from |path| into |key|.
 * If the file does not exist, it will be created with a new key.
 * On success, returns true and populates |key|.
 * On failure, returns false and |key| is undefined.
 */
bool crypto_key_import(struct crypto_key *key, const char *path);

/**
 * Signs |data| of size |size| with |key|.
 * On success, returns true and stores the signature (of size CRYPTO_SIG_SIZE)
 * in |sig|.
 * On failure, returns false and |sig| is undefined.
 */
bool crypto_key_sign(const struct crypto_key *key, void *sig, const void *data,
                     size_t size);

/**
 * Verifies the signature |sig| (of size CRYPTO_SIG_SIZE) for data |data| of
 * size |size| with key |key|.
 * On success, returns true and |valid| is set to indicate whether the
 * signature is valid.
 * If an error prevents verification, returns false and |valid| is undefined.
 */
bool crypto_key_verify(const struct crypto_key *key, const void *sig,
                       const void *data, size_t size, bool *valid);

#endif
