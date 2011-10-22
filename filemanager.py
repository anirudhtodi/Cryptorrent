import os
from glob import glob
from gzip import GzipFile
from StringIO import StringIO

class FileManager:
    file_write_progress = {}
    cached_chunks = {}

    def find_chunk(self, file_name, start_byte_number, end_byte_number):
        # Open file
        f = open(file_name, 'rb')
        # Seek to the byte we want
        ignore_bytes = f.read(start_byte_number)
        # Read the bytes to return
        bytes_to_read = f.read(end_byte_number - start_byte_number)
        print bytes_to_read
        return bytes_to_read
        # # Write the bytes to StringIO
        # output = StringIO()
        # output.write(bytes_to_read)
        # print output.getvalue()
        # # Compress the StringIO
        # gzf = GzipFile(fileobj=output, mode='ab')
        # gzf.write(output.getvalue())
        # print gzf.read()
        # gzf.close
        # # Return the compressed StringIO
        # return gzf
    
    def uncompress_chunk(self, compressed_chunk):
        print compressed_chunk
    
        # print compressed_chunk.read()
        # sio = StringIO()
        # sio.write(compressed_chunk)
        # print sio.getvalue()

        # gzf = GzipFile(fileobj=sio, mode='wb')
        # gzf.write(sio.getvalue())
        # print gzf.read()
        # gzstream = open(sio.getvalue(), 'rb')
        # sio = StringIO(gzstream)
        # gz = GzipFile(fileobj=sio, mode='rb')
        # print gz.read()
    
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
        

# a = Find_Chunk()
# compressed_chunk = a.find_chunk('test.txt', 1, 3)
# a.uncompress_chunk(compressed_chunk)
        
