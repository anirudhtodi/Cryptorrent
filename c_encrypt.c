#include "Python.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/rsa.h>
#include <openssl/engine.h>
#include <openssl/err.h>

/**
 * Encrypts string using the given public key.  Returns the number of blocks in
 * the buffer.  Places the blocks in BUF.  BUF should be large enough to hold
 * the entire string.
 */
static int encrypt(char* string, RSA* keypair, char* buf) {
  size_t len = strlen(string);
  int size = RSA_size(keypair);
  int blocks = (len - 1) / size + 1;
  int start = 0;
  int end = size - 11; // 11 bits for padding
  while (end <= len) {
    int bytes = RSA_public_encrypt(end - start, string + start, buf, rsa,
                                   RSA_PKCS1_PADDING);
    start += bytes;
    end += bytes;
    if (end > len && start < len) { end = len; }
    buf += bytes;
  }
  *buf = 0;
  return blocks;
}

/**
 * Encrypts a Python string.
 */
static PyObject* py_encrypt(PyObject* string, RSA* keypair) {
  if (PyString_Check(string)) {
    char* str = PyString_AsString(string);
    char* buf = malloc((strlen(str) - 1 / (RSA_size(keypair) - 11) + 1)
                       * RSA_size(keypair));
    int blocks = encrypt(str, keypair, buf);
    PyObject* result = PyString_FromString(buf);
    return result;
  }
  return NULL;
}



int main(int argc, char** argv) {
  RSA* rsa = RSA_generate_key(256, 17, NULL, NULL);
  int size = RSA_size(rsa);
  printf("I need at least %d bytes.\n", RSA_size(rsa));
  char* input = malloc(size + 1);
  strcpy(input, "Hello, world!");
  char *output = malloc(size + 1);
  char *result = malloc(size + 1);
  input[size] = '\0';
  output[size] = '\0';
  result[size] = '\0';

  printf("Encoding '%s'.\n", input);
  int ret_size = RSA_public_encrypt(15, input, output, rsa, RSA_PKCS1_PADDING);
  //printf("Encrypted %d bytes: '%s'.\n", ret_size, output);
  int dec_bytes = RSA_private_decrypt(ret_size, output, result, rsa, RSA_PKCS1_PADDING);
  printf("Decrypted %d bytes: '%s'.\n", dec_bytes, result);
  RSA_free(rsa);
  return 0;
}
