import os


def find_python_files(
    project_root: str,
    *,
    ignored_dirs: set[str],
    ignored_files: set[str],
) -> list[str]:
    if not os.path.exists(project_root):
        raise ValueError(f"No '{project_root}'")
    if not os.path.isdir(project_root):
        raise ValueError(f"No dir '{project_root}'")

    abs_project_root = os.path.abspath(project_root)

    # loaded_config_data, config_source_file = load_config(abs_project_root)

    # if explicit_ignored_dirs is not None:
    #     final_ignored_dirs = explicit_ignored_dirs
    #     print(
    #         f"Используются ignored_dirs, переданные как аргумент функции: {final_ignored_dirs if final_ignored_dirs else 'пусто'}"
    #     )
    # elif loaded_config_data is not None and config_source_file is not None:
    #     final_ignored_dirs = loaded_config_data.get("ignored_dirs", set())
    #     print(
    #         f"Используются ignored_dirs из конфигурационного файла ({os.path.basename(config_source_file)}): {final_ignored_dirs if final_ignored_dirs else 'пусто'}"
    #     )
    # else:
    #     final_ignored_dirs = DEFAULT_IGNORED_DIRS
    #     print(
    #         f"Конфигурационные файлы не найдены или не содержат настроек. Используются ignored_dirs по умолчанию: {final_ignored_dirs if final_ignored_dirs else 'пусто'}"
    #     )

    # Определение final_ignored_files
    # if explicit_ignored_files is not None:
    #     final_ignored_files = explicit_ignored_files
    #     print(
    #         f"Используются ignored_files, переданные как аргумент функции: {final_ignored_files if final_ignored_files else 'пусто'}"
    #     )
    # elif loaded_config_data is not None and config_source_file is not None:
    #     final_ignored_files = loaded_config_data.get("ignored_files", set())
    #     print(
    #         f"Используются ignored_files из конфигурационного файла ({os.path.basename(config_source_file)}): {final_ignored_files if final_ignored_files else 'пусто'}"
    #     )
    # else:
    #     final_ignored_files = DEFAULT_IGNORED_FILES
    #     if (
    #         loaded_config_data is None and config_source_file is None
    #     ):  # Только если вообще не было конфиг файла
    #         msg = "Конфигурационные файлы не найдены или не содержат настроек. "
    #         if final_ignored_files:
    #             msg += f"Используются ignored_files по умолчанию: {final_ignored_files}"
    #         else:
    #             msg += "Список ignored_files по умолчанию пуст."
    #         print(msg)

    python_files: list[str] = []
    for root, dirs, files in os.walk(abs_project_root, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]

        for file in files:
            if file.endswith(".py") and file not in ignored_files:
                file_path = os.path.join(root, file)
                python_files.append(file_path)
    return python_files
