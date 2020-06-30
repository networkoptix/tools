import hashlib
import os


class HashCache:
    def __init__(self, filename: str):
        self._filename = filename
        self._hash_by_path = dict()
        try:
            with open(self._filename) as file:
                line_number = 0
                for line in file:
                    line_number += 1
                    first_space_pos = line.find(' ')
                    if first_space_pos < 1:
                        print(f"ERROR: No space in line: {self._filename}:{_line_number}")
                        return
                    hash = line[:first_space_pos - 1]
                    path = line[first_space_pos + 1:]
                    if not hash or not path:
                        print(f"ERROR: No hash or path in line: {self._filename}:{_line_number}")
                        return
                    self._hash_by_path[path] = hash

        except FileNotFoundError:
            # Do nothing - create an empty cache.
            pass

    def save(self):
        with open(self._filename, "w") as file:
            for [path, hash] in self._hash_by_path.items():
                file.write(f"{hash} {path}\n")

    def update(self, path: str, hash: str) -> bool:
        result = path in self._hash_by_path
        self._hash_by_path[path] = hash
        return result


def file_as_bytes(file):
    with file:
        return file.read()


def calculate_hash(filename: str):
    return hashlib.md5(file_as_bytes(open(filename, "rb"))).hexdigest()


def create_hash_cache(cache_filename: str, source_dir: str):
    print(f"create_hash_cache({cache_filename!r}, {source_dir!r})")
    source_dir_prefix = source_dir + os.path.sep

    hashCache = HashCache(cache_filename)

    for root, subdirs, files in os.walk(source_dir):
        for file in files:
            filename = os.path.join(root, file)

            if not filename.startswith(source_dir_prefix):
                print(f"####### Suspicious file, ignoring: {filename!r}")
                continue

            rel_filename = filename[len(source_dir_prefix):]
            if (rel_filename.startswith(".git" + os.path.sep) or
                rel_filename.startswith(".hg" + os.path.sep)
            ):
                continue

            hashCache.update(rel_filename, calculate_hash(filename))

    hashCache.save()


def main():
    cwd = os.getcwd()
    create_hash_cache(os.path.join(cwd, "..", "hash_cache.txt"), cwd)


if __name__ == "__main__":
    main()
