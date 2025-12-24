from azure.storage.blob import BlobClient
import time
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_NAME = os.getenv("BLOB_ACCOUNT_NAME"),
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME"),
ACCOUNT_KEY = os.getenv("BLOB_ACCOUNT_KEY"),


def generate_random_filename(original_filename):
    print("generate_file_name")
    timestamp = str(time.time()).encode('utf-8')
    random_hash = hashlib.sha256(timestamp).hexdigest()[:12]
    file_extension = os.path.splitext(original_filename)[1]

    file_wo_extension = original_filename.split(".")[0]

    return f"{file_wo_extension}-{random_hash}{file_extension}"

def upload_blob(source_directory):
    print("inside")
    filename = os.path.basename(source_directory)
                                      
    target_filename = generate_random_filename(filename)

    blob = BlobClient.from_connection_string(conn_str="DefaultEndpointsProtocol=https;AccountName=" + ACCOUNT_NAME + ";AccountKey=" + ACCOUNT_KEY + ";EndpointSuffix=core.windows.net", container_name=CONTAINER_NAME, blob_name=target_filename)

    with open(source_directory, "rb") as data:
        blob.upload_blob(data)
    
    print("save")

    link = "https://" + ACCOUNT_NAME + ".blob.core.windows.net/" + CONTAINER_NAME + "/" + target_filename

    return link


print("starting")
file_to_upload = ""
upload_blob(file_to_upload)