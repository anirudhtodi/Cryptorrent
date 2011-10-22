#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openssl/rsa.h>
#include <openssl/engine.h>
#include <openssl/err.h>
#include <openssl/pem.h>

/**
 * Encrypts string using the given public key.  Returns the number of blocks in
 * the buffer.  Places the blocks in BUF.  BUF should be large enough to hold
 * the entire string.
 */
static int encrypt_str(char* string, RSA* keypair, char* buf) {
  size_t len = strlen(string);
  int size = RSA_size(keypair);
  int blocks = (len - 1) / size + 1;
  int start = 0;
  int end = size - 11; // 11 bits for padding
  while (end <= len) {
    int bytes = RSA_public_encrypt(end - start, (const unsigned char*)string + start,
                                   (unsigned char*)buf, keypair, RSA_PKCS1_PADDING);
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
PyObject* py_encrypt(PyObject* string, PyObject* fname) {
  if (PyString_Check(string) && PyString_Check(fname)) {
    /* First, read in public key. */
    char* keyfile = PyString_AsString(fname);
    RSA* keypair;
    FILE* fin = fopen(keyfile, "r");
    keypair = PEM_read_RSAPublicKey(fin, NULL, NULL, NULL);
    fclose(fin);

    unsigned char* str = (unsigned char*)PyString_AsString(string);
    unsigned char* buf = (unsigned char*)malloc((strlen((char*)str) - 1 /
                                                 (RSA_size(keypair) - 11) + 1)
                                                * RSA_size(keypair));
    int blocks = encrypt_str((char*)str, keypair, (char*)buf);
    PyObject* result = PyString_FromString((char*)buf);
    return result;
  }
  return NULL;
}

static PyMethodDef methods[] = {
  {"encrypt", py_encrypt, METH_VARARGS},
  {NULL, NULL, 0, NULL}
};

static PyObject* EncryptError;

PyMODINIT_FUNC initencrypt(void) {
  PyObject* m;
  m = Py_InitModule("c_encrypt", methods);
  if (m == NULL) return;
  EncryptError = PyErr_NewException("c_encrypt.error", NULL, NULL);
  Py_INCREF(EncryptError);
  PyModule_AddObject(m, "error", EncryptError);
}


int main(int argc, char** argv) {
  RSA* rsa = RSA_generate_key(512, 17, NULL, NULL);
  FILE* fout = fopen("test.pem", "w");
  PEM_write_RSA_PUBKEY(fout, rsa);
  fclose(fout);
  RSA_free(rsa);
  return 0;
}
