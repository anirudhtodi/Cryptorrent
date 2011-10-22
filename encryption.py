from subprocess import Popen, PIPE

def make_key():
    p = Popen(['openssl', 'genrsa', '-out', 'key.pem', '2048'])
    p.communicate()
    Popen(['openssl', 'rsa', '-in', 'key.pem', '-pubout', '-out',
           'pub-key.pem'])

def encrypt(data, pubkey):
    start = 0
    block_sz = 225
    result = []
    fout = open("/tmp/pub-key.pem", 'w')
    fout.write(pubkey)
    fout.close()
    while start < len(data) - 1:
        block = data[start:start + block_sz]
        p = Popen(['openssl', 'rsautl', '-encrypt', '-inkey',
                   '/tmp/pub-key.pem', '-pubin'], stdin=PIPE, stdout=PIPE)
        out, err = p.communicate(block)
        result.append(out)
        start += block_sz
        return ''.join(result)

def decrypt(data):
    start = 0
    block_sz = 256
    result = []
    while start < len(data) - 1:
        block = data[start: start + block_sz]
        p = Popen(['openssl', 'rsautl', '-decrypt', '-inkey',
                   'key.pem'], stdin=PIPE, stdout=PIPE)
        out, err = p.communicate(block)
        result.append(out)
        start += block_sz
    return ''.join(result)

def rand_string():
    import random
    import string
    s = ""
    for i in xrange(1, random.randrange(1, 5)):
        s += random.choice(string.lowercase)
    s *= random.randint(2, 124)
    return s


if __name__ == "__main__":
    for i in xrange(1000):
        s = rand_string()
        e = encrypt(s)
        r = decrypt(e)
        assert s != e and e != r and s == e
