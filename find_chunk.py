 import glob

 def find_chunk(file_name, start_byte_number, end_byte_number):
     f = open(file_name, 'rb')
     ignore_bytes = f.read(start_byte_number)
     bytes_to_read = f.read(end_byte_number - start_byte_number)
     return bytes_to_read

def find_file(file_name):
    path = glob.glob(file_name)
    if path:
        return True
    else:
        return False
    
             
