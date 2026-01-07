import os
import sys
import hashlib
import shutil
import time
from pathlib import Path
from log import Log


def get_md5_from_file(path: str) -> str:
    md5_file = hashlib.md5()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            md5_file.update(chunk)
    return md5_file.hexdigest()


def delete_redundant_data_in_replica(source: str, replica: str, log: Log) -> None:
    for root, dirs, files in os.walk(replica, topdown=False):
        for file in files:
            path_replica = os.path.join(root, file)
            if not check_if_path_source_exists(root=root, item=file, source=source, replica=replica):
                file_name = Path(path_replica).name
                dir_name = Path(path_replica).parent
                try:
                    os.remove(path_replica)
                    log.info(f"Removed redundant file '{file_name}' from '{dir_name}'")
                except OSError as msg:
                    log.warning(f"Cannot delete file '{file_name}' from directory '{dir_name}'. Reason: {msg}")
    for root, dirs, files in os.walk(replica, topdown=False):
        for dir in dirs:
            path_replica = os.path.join(root, dir)
            if not check_if_path_source_exists(root=root, item=dir, source=source, replica=replica):
                dir_name = Path(path_replica).name
                path_replica_name = Path(path_replica).parent
                try:
                    shutil.rmtree(path_replica)
                    log.info(f"Removed redundant directory '{dir_name}' from '{path_replica_name}'")
                except OSError as msg:
                    log.warning(f"Cannot delete dir '{dir_name}' from '{path_replica_name}'. Reason: {msg}")


def check_if_path_source_exists(root: str, item: str, source: str, replica: str) -> bool:
    relative_path = os.path.relpath(root, replica)
    path_source = os.path.join(source, relative_path, item)
    return Path(path_source).exists()


def sync_source_to_replica(source: str, replica: str, log: Log) -> None:
    for root, dirs, files in os.walk(source):
        relative_path = os.path.relpath(root, source)
        parent_replica_dir = os.path.normpath(os.path.join(replica, relative_path))
        for dir in dirs:
            replica_dir_path = os.path.join(replica, relative_path, dir)
            if not os.path.exists(replica_dir_path):
                dir_name = Path(replica_dir_path).name
                log.info(f"Created new directory '{dir_name}' in '{parent_replica_dir}'")
                try:
                    os.makedirs(replica_dir_path, exist_ok=True)
                except Exception as ex:
                    log.error(f"Failed creating directory '{dir_name}' in '{replica}!' Reason: {ex}")
        for file in files:
            source_file_path = os.path.join(root, file)
            replica_file_path = os.path.join(parent_replica_dir, file)
            if not os.path.exists(replica_file_path):
                created_file_name = Path(replica_file_path).name
                destination_dir = Path(replica_file_path).parent
                log.info(f"Copy file '{created_file_name}' to '{destination_dir}'")
                copy_or_overwrite_file(
                    src=source_file_path, dst=replica_file_path, log=log
                )
            else:
                md5_source_file = get_md5_from_file(source_file_path)
                md5_replica_file = get_md5_from_file(replica_file_path)
                if md5_source_file != md5_replica_file:
                    replica_dir_name = Path(replica_file_path).parent
                    replica_file_name = Path(replica_file_path).name
                    log.info(f"Overwrite file '{replica_file_name}' in '{replica_dir_name}'")
                    copy_or_overwrite_file(
                        src=source_file_path, dst=replica_file_path, log=log, is_copy=False
                    )


def is_dir_path_exists(path: str) -> bool:
    if path:
        check_path = Path(path)
        return check_path.exists() and check_path.is_dir()
    return False

def copy_or_overwrite_file(src: str, dst: str, log: Log, is_copy=True) -> None:
    dst_file_name = Path(dst).name
    exception_message = f"Failed copy file '{dst_file_name}' from source!" if is_copy else \
        f"Warning! The '{dst_file_name}' did not overwrite by original file from source!"
    try:
        shutil.copy2(src, dst)
    except Exception as ex:
        log.error(f"{exception_message} Reason: {ex}") if is_copy else log.warning(f"{exception_message} Reason: {ex}")


def main():
    source_path, replica_path, interval, amount_of_synchronization, log = validate_arguments(sys.argv)
    synchronize_data(
        source=source_path,
        replica=replica_path,
        interval_time=interval,
        amount=amount_of_synchronization,
        logger=log
    )


def synchronize_data(source: str, replica: str, interval_time: int, amount: int, logger: Log) -> None:
    i = 0
    if is_dir_path_exists(source) and is_dir_path_exists(replica):
        while i < amount:
            logger.info(f"Started {i + 1} synchronisation cycle")
            delete_redundant_data_in_replica(source=source, replica=replica, log=logger)
            sync_source_to_replica(source=source, replica=replica, log=logger)
            logger.info(f"Finished {i + 1} synchronisation cycle")
            logger.info(f"Waiting for {interval_time}s to next cycle")
            time.sleep(interval_time)
            i += 1
        logger.info(f"Finished all {i} synchronization cycles")


def validate_arguments(argv) -> tuple:
    source = None
    replica = None
    interval = 0
    amount = 0
    if len(argv) < 3:
        path_log = "log.txt"
        log = Log(path_log)
        log.error("Not demanding requirements arguments: source and replica!")
        return source, replica, interval, amount, log
    source = argv[1]
    replica = argv[2]
    interval = argv[3] if len(argv) >= 4 else 0
    amount = argv[4] if len(argv) >= 5 else 0
    path_log = argv[5] if len(argv) == 6 else "log.txt"
    log = Log(path_log)
    if amount == 0:
        log.warning("Amount is 0 – skipping synchronization!")
    if not is_dir_path_exists(source):
            log.error(f"Source path '{source}' does not exist!")
    if not is_dir_path_exists(replica):
        log.error(f"Replica path '{replica}' does not exist!")
    try:
        int_interval = int(interval)
        int_amount_of_synchronization = int(amount)
    except ValueError:
        int_interval = 0
        int_amount_of_synchronization = 0
        log.error("Interval and amount_of_synchronization must be integers!")
    if int_interval < 0 or int_amount_of_synchronization < 0:
        log.error("Interval or amount_of_synchronization must be higher than 0!")
        int_interval = 0
        int_amount_of_synchronization = 0
    return source, replica, int_interval, int_amount_of_synchronization, log


if __name__ == '__main__':
    main()
