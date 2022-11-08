#include "crypto.h"

#include <openssl/bio.h>
#include <openssl/bn.h>
#include <openssl/ec.h>
#include <openssl/pem.h>
#include <openssl/sha.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "util.h"

/* Signing nonce. */
static BIGNUM *g_nonce;

static bool generate_key(const char *path)
{
	bool ret = false;
	EC_KEY *key = NULL;
	FILE *fp = NULL;

	key = EC_KEY_new_by_curve_name(NID_X9_62_prime256v1);
	if (!key) {
		fprintf(stderr, "generate_key: failed to create key\n");
		goto cleanup;
	}

	if (EC_KEY_generate_key(key) != 1) {
		fprintf(stderr, "generate_key: failed to generate key\n");
		goto cleanup;
	}

	fp = fopen(path, "w");
	if (!fp) {
		perror("fopen");
		goto cleanup;
	}

	if (!PEM_write_ECPrivateKey(fp, key, NULL, NULL, 0, NULL, NULL)) {
		fprintf(stderr, "generate_key: failed to write key\n");
		goto cleanup;
	}

	ret = true;

cleanup:
	EC_KEY_free(key);
	if (fp)
		fclose(fp);
	return ret;
}

bool crypto_key_import(struct crypto_key *key, const char *path)
{
	bool ret = false;
	EC_KEY *ec_key = NULL;
	char *pem_privkey = NULL, *pem_pubkey = NULL;
	BIO *bio_privkey = NULL, *bio_pubkey = NULL;

	if (access(path, F_OK) == -1) {
		if (!generate_key(path))
			goto cleanup;
	}

	pem_privkey = read_file(path, NULL);
	if (!pem_privkey)
		goto cleanup;

	bio_privkey = BIO_new_mem_buf(pem_privkey, -1);
	if (!bio_privkey) {
		fprintf(stderr, "crypto_key_import: failed to create privkey BIO\n");
		goto cleanup;
	}

	ec_key = PEM_read_bio_ECPrivateKey(bio_privkey, NULL, NULL, NULL);
	if (!ec_key) {
		fprintf(stderr, "crypto_key_import: failed to read privkey\n");
		goto cleanup;
	}

	bio_pubkey = BIO_new(BIO_s_mem());
	if (!bio_pubkey) {
		fprintf(stderr, "crypto_key_import: failed to create pubkey BIO\n");
		goto cleanup;
	}

	if (!PEM_write_bio_EC_PUBKEY(bio_pubkey, ec_key)) {
		fprintf(stderr, "crypto_key_import: failed to write pubkey\n");
		goto cleanup;
	}

	char *pubkey_data;
	long pubkey_size = BIO_get_mem_data(bio_pubkey, &pubkey_data);

	pem_pubkey = malloc(pubkey_size + 1);
	if (!pem_pubkey) {
		perror("malloc");
		goto cleanup;
	}

	memcpy(pem_pubkey, pubkey_data, pubkey_size);
	pem_pubkey[pubkey_size] = '\0';

	key->pem_privkey = pem_privkey;
	key->pem_pubkey = pem_pubkey;
	key->ec_key = ec_key;

	ret = true;

cleanup:
	if (!ret) {
		EC_KEY_free(ec_key);
		free(pem_privkey);
		free(pem_pubkey);
	}
	BIO_vfree(bio_privkey);
	BIO_vfree(bio_pubkey);
	return ret;
}

bool crypto_key_sign(const struct crypto_key *key, void *sig, const void *data,
                     size_t size)
{
	unsigned char hash[SHA256_DIGEST_LENGTH];
	SHA256(data, size, hash);

	if (g_nonce == NULL) {
		/* BUG: static nonce */
		g_nonce = BN_new();
		BN_rand(g_nonce, 256, -1, false);
	}

	BN_CTX *ctx = BN_CTX_new();

	const EC_GROUP *group = EC_KEY_get0_group(key->ec_key);

	BIGNUM *kinv;
	{
		BIGNUM *n = BN_new();
		EC_GROUP_get_order(group, n, ctx);
		kinv = BN_mod_inverse(NULL, g_nonce, n, ctx);
		BN_free(n);
	}

	BIGNUM *rp;
	{
		EC_POINT *kG = EC_POINT_new(group);
		EC_POINT_mul(group, kG, g_nonce, NULL, NULL, ctx);

		rp = BN_new();
		EC_POINT_get_affine_coordinates_GFp(group, kG, rp, NULL, ctx);

		EC_POINT_free(kG);
	}

#if 0
	fprintf(stderr, "d = ");
	BN_print_fp(stderr, EC_KEY_get0_private_key(key->ec_key));
	fprintf(stderr, "\nk = ");
	BN_print_fp(stderr, g_nonce);
	fprintf(stderr, "\nkinv = ");
	BN_print_fp(stderr, kinv);
	fprintf(stderr, "\nrp = ");
	BN_print_fp(stderr, rp);
	fprintf(stderr, "\n");
#endif

	ECDSA_SIG *ec_sig =
	    ECDSA_do_sign_ex(hash, sizeof(hash), kinv, rp, key->ec_key);

	BN_free(kinv);
	BN_free(rp);
	BN_CTX_free(ctx);

	if (!ec_sig) {
		fprintf(stderr, "crypto_key_sign: failed to generate signature\n");
		return false;
	}

	const BIGNUM *r, *s;
	ECDSA_SIG_get0(ec_sig, &r, &s);

#if 0
	fprintf(stderr, "r = ");
	BN_print_fp(stderr, r);
	fprintf(stderr, "\ns = ");
	BN_print_fp(stderr, s);
	fprintf(stderr, "\n");
#endif

	BN_bn2binpad(r, sig, CRYPTO_SIG_SIZE / 2);
	BN_bn2binpad(s, (unsigned char *)sig + CRYPTO_SIG_SIZE / 2,
	             CRYPTO_SIG_SIZE / 2);

	ECDSA_SIG_free(ec_sig);

	return true;
}

bool crypto_key_verify(const struct crypto_key *key, const void *sig,
                       const void *data, size_t size, bool *valid)
{
	unsigned char hash[SHA256_DIGEST_LENGTH];
	SHA256(data, size, hash);

	BIGNUM *r = BN_bin2bn(sig, CRYPTO_SIG_SIZE / 2, NULL);
	BIGNUM *s = BN_bin2bn((unsigned char *)sig + CRYPTO_SIG_SIZE / 2,
	                      CRYPTO_SIG_SIZE / 2, NULL);

	ECDSA_SIG *ec_sig = ECDSA_SIG_new();
	ECDSA_SIG_set0(ec_sig, r, s); // ec_sig owns r and s now.
	int ret = ECDSA_do_verify(hash, sizeof(hash), ec_sig, key->ec_key);
	ECDSA_SIG_free(ec_sig);

	if (ret == -1) {
		fprintf(stderr, "crypto_key_verify: failed to verify signature\n");
		return false;
	}

	*valid = (ret == 1);
	return true;
}
