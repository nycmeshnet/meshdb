import logging

import boto3


# Returns the key to the most recently modified object in an S3 bucket
def get_most_recent_object(bucket_name: str, prefix: str) -> str | None:
    s3_client = boto3.client("s3")
    objects = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if "Contents" not in objects:
        logging.error(f"No objects found in '{bucket_name}/{prefix}'.")
        return None

    most_recent_object = max(objects["Contents"], key=lambda obj: obj["LastModified"])

    object_key = most_recent_object["Key"]
    last_modified = most_recent_object["LastModified"]

    logging.info(f"Most recent object: {object_key}, Last modified: {last_modified}")
    return object_key
