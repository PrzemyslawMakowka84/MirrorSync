import os
import sys
import hashlib
import shutil
import time
from pathlib import Path
from log import Log


def get_md5_from_first_file(source_path: str) -> str | None:
    md5_first_file = None
    if source_path:
        for root, dirs, files in os.walk(source_path):
            if files:
                file = files[0]
                first_file_path = os.path.join(root, file)
                md5_first_file = get_md5_from_file(first_file_path)
                return md5_first_file
    return md5_first_file


def get_md5_from_file(path: str) -> str:
    md5_file = hashlib.md5()
    with open(path, "rb") as file:
        for chuck in iter(lambda: file.read(4096), b""):
            md5_file.update(chuck)
    return md5_file.hexdigest()


def delete_redundant_data_in_replica(source: str, replica: str, log: Log, check_dir: bool) -> None:
    for root, dirs, files in os.walk(replica, topdown=not check_dir):
        items = dirs if check_dir else files
        item_remove = "directory" if check_dir else "file"
        remove_func = shutil.rmtree if check_dir else os.remove

        for item in items:
            path_replica = os.path.join(root, item)
            relative_path = os.path.relpath(root, replica)
            path_source = os.path.join(source, relative_path, item)
            if not os.path.exists(path_source):
                item_name = Path(path_replica).name
                parent_path_replica = Path(path_replica).parent
                log.info(f"Removed redundant {item_remove} '{item_name}' from '{parent_path_replica}'")
                remove_func(path_replica)


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
                    log.info(f"Failed creating directory '{dir_name}' in '{replica}!' Reason: {ex}")
                    raise
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


def copy_or_overwrite_file(src: str, dst: str, log: Log, is_copy=True) -> None:
    dst_file_name = Path(dst).name
    exception_message = f"Failed copy file '{dst_file_name}' from source!" if is_copy else \
        f"Warning! The '{dst_file_name}' did not overwrite by original file from source!"
    try:
        shutil.copy2(src, dst)
    except Exception as ex:
        log.warning(f"{exception_message} Reason: {ex}")
        if is_copy:
            raise

def main():
    source_path, replica_path, interval, amount_of_synchronization, log = validate_arguments(sys.argv)
    get_md5_from_first_file(source_path)
    synchronize_data(
        source=source_path,
        replica=replica_path,
        interval_time=interval,
        amount=amount_of_synchronization,
        logger=log
    )

def synchronize_data(source: str, replica: str, interval_time: int, amount: int, logger: Log) -> None:
    i = 0
    if source and replica:
        while i < amount:
            logger.info(f"Started {i + 1} synchronisation cycle")
            delete_redundant_data_in_replica(source=source, replica=replica, log=logger, check_dir=True)
            delete_redundant_data_in_replica(source=source, replica=replica, log=logger, check_dir=False)
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
    path_log = None
    log = None
    if len(argv) == 6:
        source = argv[1]
        replica = argv[2]
        interval = argv[3]
        amount = argv[4]
        path_log = sys.argv[5]
    if source:
        log_dir_name = Path(path_log).parent
        log = Log("log.txt") if log_dir_name.exists() else Log(path_log)
        if not os.path.exists(source):
            log.error(f"Source path '{source}' does not exists!")
            source = None
    if replica:
        if not os.path.exists(replica):
            log.error(f"Replica path '{replica}' does not exists!")
            replica = None
    try:
        int_interval = int(interval)
        int_amount_of_synchronization = int(amount)
    except ValueError:
        int_interval = 0
        int_amount_of_synchronization = 0
        log.error("Interval and amount_of_synchronization must be integers!")
    if int_interval < 0 or int_amount_of_synchronization < 0:
        log.error("Internal or amount_of_synchronization must be higher than 0!")
        int_interval = 0
        int_amount_of_synchronization = 0
    return source, replica, int_interval, int_amount_of_synchronization, log


if __name__ == '__main__':
    main()
