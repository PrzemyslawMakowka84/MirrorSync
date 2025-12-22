import os
import sys
import hashlib
import shutil
import time
from datetime import datetime
from pathlib import Path


class Log:
    def __init__(self, path_to_log_file: str):
        self.__log_path = path_to_log_file
        self.__log_list = []

    def info(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"{timestamp} {message}"
        print(line)
        self.__log_list.append(line)

    def save_to_file(self):
        with open(self.__log_path, "w", encoding="UTF-8") as file:
            for line in self.__log_list:
                file.write(f"{line}\n")


def get_md5_from_first_file(source_path: str) -> str | None:
    md5_first_file = None
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
        log.info(f"{exception_message} Reason: {ex}")
        if is_copy:
            raise


def synchronize_data(source: str, replica: str, interval_time: int, amount: int, path_log: str) -> None:
    i = 0
    log = Log(path_log)
    try:
        while i < amount:
            log.info(f"Started {i+1} synchronisation cycle")
            delete_redundant_data_in_replica(source=source, replica=replica, log=log, check_dir=True)
            delete_redundant_data_in_replica(source=source, replica=replica, log=log, check_dir=False)
            sync_source_to_replica(source=source, replica=replica, log=log)
            log.info(f"Finished {i+1} synchronisation cycle")
            log.info(f"Waiting for {interval_time}s to next cycle\n")
            time.sleep(interval_time)
            i += 1
    finally:
        log.info(f"Finished all {i} synchronization cycles")
        log.save_to_file()


def validate_arguments(
        source_path: str,
        replica_path: str,
        interval: str,
        amount_of_synchronization: str,
        log_path: str) -> tuple:
        if not os.path.exists(source_path):
            raise ValueError(f"Source path '{source_path}' does not exists!")
        if not os.path.exists(replica_path):
            raise ValueError(f"Replica path '{replica_path}' does not exists!")
        log_dir_name = Path(log_path).parent
        if not log_dir_name.exists():
            raise ValueError(f"Directory '{log_dir_name}' for log file does not exists!")
        try:
            int_interval = int(interval)
            int_amount_of_synchronization = int(amount_of_synchronization)
        except ValueError:
            raise ValueError("Interval and amount_of_synchronization must be integers!")
        if int_interval < 0 or int_amount_of_synchronization < 0:
            raise ValueError("Internal and amount_of_synchronization must be higher than 0!")
        return source_path, replica_path, int_interval, int_amount_of_synchronization, log_path


if __name__ == '__main__':
        source_path = sys.argv[1]
        replica_path = sys.argv[2]
        interval = sys.argv[3]
        amount_of_synchronization = sys.argv[4]
        log_path = sys.argv[5]
        source_path, replica_path, interval, amount_of_synchronization, log_path = validate_arguments(
            source_path=source_path,
            replica_path=replica_path,
            interval=interval,
            amount_of_synchronization=amount_of_synchronization,
            log_path=log_path
        )
        get_md5_from_first_file(source_path)
        synchronize_data(
            source=source_path,
            replica=replica_path,
            interval_time=interval,
            amount=amount_of_synchronization,
            path_log=log_path
        )
