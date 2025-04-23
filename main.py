import os
import time
import sys
import shutil # Для получения ширины терминала
import datetime # Для временных меток
import errno # Для более детальной обработки ошибок OSError

# --- Конфигурация ---
# Укажите полные пути, используя raw strings (r"...") или двойные слеши ("\\")
INPUT_FILENAME = r'D:\Base\Playlists\broad.int'
OUTPUT_FILENAME = r'D:\Base\Playlists\broad.txt'

# Список подстрок-исключений.
EXCEPTION_SUBSTRINGS = [
    r"\Jingles",
    r"/Jingles",
    r"\Promo",
    r"/Promo"
]
DEFAULT_OUTPUT_STRING = "Radio Muzlo"
# Начальная позиция имени файла (индексация с 0)
FILENAME_START_POS = 269
# Список известных расширений для поиска конца имени файла
KNOWN_EXTENSIONS = ['.mp3', '.wav', '.aac', '.flac', '.ogg', '.wma', '.m4a']
# Пауза между проверками файла в секундах
LOOP_PAUSE_SECONDS = 3
# Кодировка входного файла
INPUT_ENCODING = 'cp1251'
# Кодировка выходного файла
OUTPUT_ENCODING = 'utf-8'
# Префикс для вывода в консоль (статусная строка)
CONSOLE_STATUS_PREFIX = "Текущее значение: "
# --- Конец конфигурации ---

def get_terminal_width(default=80):
    """Возвращает ширину терминала или значение по умолчанию."""
    try:
        columns, _ = shutil.get_terminal_size(fallback=(default, 24))
        return columns
    except OSError:
        return default

def clear_line(terminal_width):
    """Печатает пустую строку для очистки текущей строки консоли."""
    clear_str = ' ' * terminal_width
    print(f"\r{clear_str}\r", end='')

def log_message(message, level="INFO"):
    """Выводит сообщение с временной меткой и уровнем в консоль."""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    terminal_width = get_terminal_width()
    clear_line(terminal_width)
    print(f"[{timestamp}] [{level}] {message}")

def print_status_line(message, terminal_width):
    """Печатает сообщение в одну строку, перезаписывая предыдущее."""
    clear_line(terminal_width)
    print(message, end='', flush=True)

def extract_filename_from_line(line, start_pos, known_extensions):
    """Извлекает полный путь к файлу из строки."""
    if len(line) <= start_pos:
        return None
    potential_path_part = line[start_pos:]
    earliest_end_index_in_part = -1
    potential_path_part_lower = potential_path_part.lower()
    for ext in known_extensions:
        try:
            found_pos = potential_path_part_lower.index(ext.lower())
            current_end_index = found_pos + len(ext)
            if earliest_end_index_in_part == -1 or current_end_index < earliest_end_index_in_part:
                 earliest_end_index_in_part = current_end_index
        except ValueError:
            continue
    if earliest_end_index_in_part != -1:
        full_path = line[start_pos : start_pos + earliest_end_index_in_part]
        return full_path.strip()
    else:
        return None

def check_exceptions(filepath, exceptions):
    """Проверяет наличие исключений в пути."""
    if not filepath:
        return False
    for exc_substring in exceptions:
        if exc_substring.lower() in filepath.lower():
            return True
    return False

def get_filename_without_extension(filepath):
    """Возвращает имя файла без расширения."""
    if not filepath:
        return ""
    try:
        base_name = os.path.basename(filepath)
        filename_no_ext, _ = os.path.splitext(base_name)
        return filename_no_ext
    except Exception as e:
        log_message(f"Ошибка при обработке пути '{filepath}': {e}", "WARNING")
        return ""

def ensure_dir_exists(filepath):
    """Проверяет и создает директорию для указанного пути файла."""
    directory = os.path.dirname(filepath)
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            log_message(f"Создана директория: '{directory}'", "INFO")
        except OSError as e:
            # Проверяем, не была ли директория создана другим процессом между проверкой и созданием
            if e.errno != errno.EEXIST:
                log_message(f"Не удалось создать директорию '{directory}': {e}", "CRITICAL")
                return False # Не удалось создать директорию
            else:
                # Директория уже существует (была создана другим процессом) - это нормально
                 pass
    return True # Директория существует или успешно создана

def process_broadcast_log(input_file, output_file, start_pos, extensions, exceptions, default_output, input_encoding, output_encoding):
    """
    Читает, обрабатывает и атомарно записывает результат.
    Возвращает строку, которая была записана в файл, или None при ошибке записи.
    """
    output_string = default_output
    operation_status = "OK"

    # --- Чтение и обработка входного файла ---
    try:
        if not os.path.exists(input_file):
             operation_status = f"Файл '{input_file}' не найден"
        else:
            with open(input_file, 'r', encoding=input_encoding) as infile:
                first_line = infile.readline()
                if not first_line:
                    operation_status = f"Файл '{input_file}' пуст"
                else:
                    full_path = extract_filename_from_line(first_line, start_pos, extensions)
                    if not full_path:
                        operation_status = f"Не удалось извлечь путь из '{input_file}'"
                    else:
                        is_exception = check_exceptions(full_path, exceptions)
                        if is_exception:
                            operation_status = f"Путь содержит исключение"
                        else:
                            filename_no_ext = get_filename_without_extension(full_path)
                            if not filename_no_ext:
                                operation_status = f"Не удалось получить имя из '{full_path}'"
                            else:
                                output_string = filename_no_ext
                                operation_status = "OK"
    except (IOError, OSError, PermissionError) as e:
        log_message(f"Ошибка доступа при чтении '{input_file}': {e}", "ERROR")
        operation_status = "Read Error"
    except UnicodeDecodeError as e:
         log_message(f"Ошибка декодирования '{input_file}' ({input_encoding}): {e}", "ERROR")
         operation_status = "Decode Error"
    except Exception as e:
        log_message(f"Неожиданная ошибка чтения/обработки '{input_file}': {e}", "ERROR")
        operation_status = "Processing Error"

    # --- АТОМАРНАЯ ЗАПИСЬ РЕЗУЛЬТАТА ---
    temp_output_file = output_file + ".tmp"

    # 1. Убедиться, что директория существует
    if not ensure_dir_exists(output_file):
        return None # Не можем продолжать без директории

    # 2. Запись во временный файл и замена
    try:
        # 2a. Запись во временный файл
        try:
            with open(temp_output_file, 'w', encoding=output_encoding) as outfile:
                outfile.write(output_string)
        except (IOError, OSError) as e:
            log_message(f"Ошибка записи во временный файл '{temp_output_file}': {e}", "CRITICAL")
            if os.path.exists(temp_output_file):
                try: os.remove(temp_output_file)
                except OSError: pass # Игнорируем ошибку удаления здесь
            return None # Ошибка записи

        # 2b. Атомарная замена
        try:
            os.replace(temp_output_file, output_file)
        except OSError as e:
            log_message(f"Ошибка замены '{output_file}' временным файлом '{temp_output_file}': {e}", "CRITICAL")
            if os.path.exists(temp_output_file):
                 try: os.remove(temp_output_file)
                 except OSError: pass
            return None # Ошибка замены

        # Успех!
        return output_string

    except Exception as e:
        # Общий обработчик
        log_message(f"Неожиданная ошибка при записи файла '{output_file}': {e}", "CRITICAL")
        if os.path.exists(temp_output_file):
            try: os.remove(temp_output_file)
            except OSError: pass
        return None # Сигнализируем об ошибке записи


# --- Запуск основного цикла ---
if __name__ == "__main__":

    log_message("Проверка директорий при запуске...", "INFO")
    input_dir_ok = os.path.exists(os.path.dirname(INPUT_FILENAME)) or INPUT_FILENAME == os.path.basename(INPUT_FILENAME)
    output_dir_ok = ensure_dir_exists(OUTPUT_FILENAME)

    if not input_dir_ok:
        log_message(f"Директория для входного файла '{INPUT_FILENAME}' не найдена!", "WARNING")
        # Можно решить, продолжать ли работу, если входной директории нет

    if not output_dir_ok:
         log_message(f"Не удалось создать/обеспечить директорию для выходного файла '{OUTPUT_FILENAME}'. Проверьте права доступа.", "CRITICAL")
         log_message("Скрипт не может продолжить работу.", "CRITICAL")
         sys.exit(1) # Выход с кодом ошибки

    # --- Основная информация о запуске ---
    log_message(f"Запуск скрипта мониторинга файла '{INPUT_FILENAME}'.", "INFO")
    log_message(f"Запись в '{OUTPUT_FILENAME}' (Кодировка: {OUTPUT_ENCODING}).", "INFO")
    log_message(f"Пауза: {LOOP_PAUSE_SECONDS} сек. Кодировка чтения: {INPUT_ENCODING}", "INFO")
    log_message(f"Строка по умолчанию: '{DEFAULT_OUTPUT_STRING}'", "INFO")
    print("Для остановки нажмите Ctrl+C.") # Обычный print для стартового сообщения

    last_status_message = ""

    try:
        while True:
            terminal_width = get_terminal_width()

            written_value = process_broadcast_log(
                INPUT_FILENAME,
                OUTPUT_FILENAME,
                FILENAME_START_POS,
                KNOWN_EXTENSIONS,
                EXCEPTION_SUBSTRINGS,
                DEFAULT_OUTPUT_STRING,
                INPUT_ENCODING,
                OUTPUT_ENCODING
            )

            current_status_message = ""
            if written_value is not None:
                current_status_message = f"{CONSOLE_STATUS_PREFIX}{written_value}"
            else:
                 current_status_message = f"{CONSOLE_STATUS_PREFIX}ОШИБКА ЗАПИСИ!"

            if current_status_message != last_status_message:
                print_status_line(current_status_message, terminal_width)
                last_status_message = current_status_message

            time.sleep(LOOP_PAUSE_SECONDS)

    except KeyboardInterrupt:
        log_message("Обнаружено нажатие Ctrl+C. Завершение работы...", "INFO")
    except Exception as e:
        log_message(f"Критическая ошибка в главном цикле: {e}", "CRITICAL")
    finally:
        terminal_width = get_terminal_width()
        clear_line(terminal_width)
        log_message("Скрипт остановлен.", "INFO")
        sys.exit(0)