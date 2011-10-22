from glob import glob
from gzip import GzipFile
from StringIO import StringIO

class Find_Chunk():
    def find_chunk(file_name, start_byte_number, end_byte_number):
        # Open file
        f = open(file_name, 'rb')
        # Seek to the byte we want
        ignore_bytes = f.read(start_byte_number)
        # Read the bytes to return
        bytes_to_read = f.read(end_byte_number - start_byte_number)
        # Write the bytes to StringIO
        output = StringIO()
        output.write(bytes_to_read)
        # Compress the StringIO
        gzf = GzipFile(fileobj=output, mode='wb')
        gzf.write(output)
        gzf.close
        # Return the compressed StringIO
        return gzf
    
    def find_file(file_name):
        # Check if the file_name exists in our current directory
        path = glob(file_name)
        if path:
            return True
        else:
            return False
             
