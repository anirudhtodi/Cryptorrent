import os
from glob import glob
import cStringIO
import binascii
import zlib

class FileManager:
    file_write_progress = {}
    cached_chunks = {}

    def find_chunk(self, file_name, start_byte_number, end_byte_number):
        f = open(file_name, 'rb')
        ignore_bytes = f.read(start_byte_number)
        bytes_to_read = f.read(end_byte_number - start_byte_number)
        return zlib.compress(bytes_to_read, 9)

    def uncompress_chunk(self, compressed_chunk):
        return zlib.decompress(compressed_chunk)
    
    def find_file(self, file_name):
        # Check if the file_name exists in our current directory
        path = glob(file_name)
        if path:
            return os.path.getsize(file_name)
        else:
            return None

    def receive_chunk(self, file_name, start_byte, finish_byte, chunk):
        if file_name not in self.file_write_progress:
            self.file_write_progress[file_name] = 0
        progress = self.file_write_progress[file_name]
        if start_byte == progress:
            f = open(file_name, "ab")
            f.write(chunk)
            progress = finish_byte + 1
            while ((file_name, progress) in self.cached_chunks):
                f.write(self.cached_chunks[(file_name, progress)][0])
                progress = self.cached_chunks[(file_name, progress)][1] + 1
            f.close()
        else:
            self.cached_chunks[(file_name, start_byte)] = (chunk, finish_byte)
        self.file_write_progress[file_name] = progress
        
if __name__ == "__main__":
    f = FileManager()
    chunk = f.find_chunk("tozip.txt", 0, 16)
    chunk = f.uncompress_chunk(chunk)
    print chunk


# a = Find_Chunk()
# compressed_chunk = a.find_chunk('test.txt', 1, 3)
# a.uncompress_chunk(compressed_chunk)
