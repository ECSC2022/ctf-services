package pow

import (
  "errors"
  "crypto/rand"
  "fmt"
  "io"
  "log"
  "encoding/hex"
  "encoding/binary"
  "encoding/json"

  "golang.org/x/crypto/chacha20poly1305"
  "golang.org/x/crypto/curve25519"
  "golang.org/x/crypto/hkdf"
  "crypto/sha256"
)


type PoW struct {
  Difficulty    uint8
  Hash          string
  SessionPubKey []byte
  Ciphertext    []byte
  Salt          []byte
  Nonce         []byte
}


func aeadEncrypt(key, plaintext []byte, nonce []byte) ([]byte, error) {
  aead, err := chacha20poly1305.New(key)
  if err != nil {
    return nil, err
  }
  return aead.Seal(nil, nonce, plaintext, nil), nil
}


func aeadDecrypt(key, ciphertext []byte, nonce []byte) ([]byte, error) {
  aead, err := chacha20poly1305.New(key)
  if err != nil {
    return nil, err
  }
  return aead.Open(nil, nonce, ciphertext, nil)
}


func CrackPoW(pow_data []byte, botPrivKey []byte,
) (target []byte, err error)  {
    
    var pow PoW
    err = json.Unmarshal(pow_data, &pow)
    if err != nil {
        log.Fatalf("Error occured during marshaling. Error: %s", err.Error())
    }
    fmt.Printf("PoW JSON: %s\n", pow)

    sharedSecret, err := curve25519.X25519(botPrivKey, pow.SessionPubKey)
    if err != nil {
      return
    }

    h := hkdf.New(sha256.New, sharedSecret, nil, []byte(""))
    wrappingKey := make([]byte, chacha20poly1305.KeySize)
    _, err = io.ReadFull(h, wrappingKey); 
    if err != nil {
      return
    }

    // Get the plaintext target
    plain, err := aeadDecrypt(wrappingKey, pow.Ciphertext, pow.Nonce)
    if err != nil {
      return
    }
    // Verify if somebody tampered with the PoW
    
    hash := sha256.Sum256(plain)
    hexhash := hex.EncodeToString(hash[:])
    if hexhash != pow.Hash{
      err = errors.New("Hashes don't match")
      return
    }

    // If we use this we need to also make sure that we check if somebody tampered with the 
    // plaintext data, e.g. check if the target they sent matches the difficulty they sent
    // like in python. But I realized we might not need this here, 
    // since the bots are most likely in python anyway...
    // mask := binary.BigEndian.Uint64(proof[8:]) & ^((1<<difficulty)-1) 
    // masked_bytes := make([]byte, 8)
    // binary.BigEndian.PutUint64(masked_bytes, masked)
    // target := append(proof[:8],masked_bytes[:]...)

    // fmt.Println(plain)
    


    target = plain

    return
}


func NewPoW(
  difficulty uint8,
  botPublicKey []byte,
  log *log.Logger,
) (pow *PoW, target uint64, err error) {
  // Generate private key
  ephemeral := make([]byte, curve25519.ScalarSize)
  _, err = rand.Read(ephemeral); 
  if err != nil {
    return 
  }
  public, err := curve25519.X25519(ephemeral, curve25519.Basepoint)
  if err != nil {
    return 
  }

  // Shared Secret
  sharedSecret, err := curve25519.X25519(ephemeral, botPublicKey)
  if err != nil {
    return
  }

  //salt := make([]byte, 0, len(public)+len(botPublicKey))
  //salt = append(salt, public...)
  //salt = append(salt, botPublicKey...)
  h := hkdf.New(sha256.New, sharedSecret, nil, []byte(""))
  wrappingKey := make([]byte, chacha20poly1305.KeySize)
  _, err = io.ReadFull(h, wrappingKey); 
  if err != nil {
    return
  }

  proof := make([]byte, 16)
  _, err = rand.Read(proof); 
  if err != nil {
    return 
  }

  nonce := make([]byte, 12)
  _, err = rand.Read(nonce); 
  if err != nil {
    return 
  }

  cipher, err := aeadEncrypt(wrappingKey, proof, nonce)
  if err != nil {
    return
  }

  hash := sha256.Sum256(proof)

  target = binary.BigEndian.Uint64(proof[8:]) & ((1<<difficulty)-1) 
  masked := binary.BigEndian.Uint64(proof[8:]) & ^((1<<difficulty)-1) 
  masked_bytes := make([]byte, 8)
  binary.BigEndian.PutUint64(masked_bytes, masked)
  salt := append(proof[:8],masked_bytes[:]...)

  // Calculate public key
  pow = &PoW{
    Difficulty: difficulty,
    Salt: salt,
    Nonce: nonce,
    Hash: hex.EncodeToString(hash[:]),
    SessionPubKey:  public,
    Ciphertext: cipher,
  }

  return
}



type X25519Recipient struct {
  theirPublicKey []byte
}




