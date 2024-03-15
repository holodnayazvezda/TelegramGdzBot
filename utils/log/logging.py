def log_info(filename: str, info: str) -> None:
    with open(filename, "a+") as log_file:
        log_file.write(f"{info}\n")