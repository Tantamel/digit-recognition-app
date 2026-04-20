import tkinter as tk
import os
import shutil
import threading
from tkinter import filedialog, ttk, messagebox
from pipeline import process_image


results_data = []

def rename_files():
    global results_data
    path = folder_path.get() + "_copy"

    for old_name, new_name, status in results_data:

        if not new_name:
            continue

        old_path = os.path.join(path, old_name)
        new_path = os.path.join(path, new_name + ".jpg")

        try:
            os.rename(old_path, new_path)
        except Exception as e:
            print(f"Ошибка: {old_name} → {e}")

def process_folder():
    global results_data

    original_path = folder_path.get()
    if not original_path:
        return

    copy_path = original_path + "_copy"

    if os.path.exists(copy_path):
        shutil.rmtree(copy_path)

    shutil.copytree(original_path, copy_path)
    path = copy_path

    # очистка таблицы
    for item in tree.get_children():
        tree.delete(item)

    files = [
        os.path.join(path, f)
        for f in os.listdir(path)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]

    total_files = len(files)
    progress["maximum"] = total_files
    progress["value"] = 0

    results_data.clear()
    temp_results = []
    number_counts = {}

    good_count = 0
    warn_count = 0
    bad_count = 0

    for file_path in files:

        filename = os.path.basename(file_path)

        # 🔥 ВАЖНО — теперь вся магия тут
        number, status, conf = process_image(file_path)

        # --- если не распознали ---
        if not number:
            new_name = "!" + filename
            temp_results.append((filename, new_name, status))
            bad_count += 1
            continue

        # --- дубликаты ---
        count = number_counts.get(number, 0)
        new_name = number if count == 0 else f"{number}_{count}"
        number_counts[number] = count + 1

        # --- статус ---
        if status == "отлично":
            good_count += 1
        elif status == "!не уверена":
            warn_count += 1
            new_name = "!" + new_name
        else:
            bad_count += 1
            new_name = "!" + new_name

        temp_results.append((filename, new_name, status))

        # --- прогресс ---
        progress_value = progress["value"] + 1

        def update_ui():
            progress["value"] = progress_value
            status_label.config(
                text=f"Обработано: {progress_value} / {total_files}"
            )

        root.after(0, update_ui)

    # --- сортировка ---
    priority = {"!пересмотр": 0, "!не уверена": 1, "отлично": 2}
    temp_results.sort(key=lambda x: priority.get(x[2], 3))

    for i, (old_name, new_name, status) in enumerate(temp_results):

        tag = (
            "good" if status == "отлично"
            else "warn" if status == "!не уверена"
            else "bad"
        )

        tree.insert(
            "", "end",
            iid=str(i),
            values=(old_name, new_name, status),
            tags=(tag,)
        )

        results_data.append((old_name, new_name, status))

    def final_update():
        status_label.config(
            text=f"Всего: {total_files} | ✔ {good_count} | ⚠ {warn_count} | ❌ {bad_count}"
        )

    root.after(0, final_update)

# --- создание окна ---
root = tk.Tk()
root.title("Переименование файлов")
root.geometry("800x550")

# --- переменная для пути ---
folder_path = tk.StringVar()

# --- функция выбора папки ---
def choose_folder():
    path = filedialog.askdirectory()
    if path:
        folder_path.set(path)

# --- функция трединга ---
def start_processing():
    thread = threading.Thread(target=process_folder)
    thread.daemon = True
    thread.start()

# =========================
# 🔹 БЛОК 1 — выбор папки
# =========================
top_frame = tk.Frame(root)
top_frame.pack(pady=10)

btn_select = tk.Button(top_frame, text="Выбрать папку", command=choose_folder, width=20)
btn_select.pack(side="left", padx=5)

label_path = tk.Label(top_frame, textvariable=folder_path)
label_path.pack(side="left", padx=10)

# =========================
# 🔹 БЛОК 2 — управление
# =========================
control_frame = tk.Frame(root)
control_frame.pack(pady=10)

btn_start = tk.Button(
    control_frame,
    text="Старт",
    command=start_processing,
    width=20,
    bg="#4CAF50",
    fg="white"
)
btn_start.pack(side="left", padx=5)

btn_rename = tk.Button(
    control_frame,
    text="Переименовать",
    command=rename_files,
    width=20,
    bg="#2196F3",
    fg="white"
)
btn_rename.pack(side="left", padx=5)

# =========================
# 🔹 статус и прогресс
# =========================
status_label = tk.Label(root, text="Готово к запуску")
status_label.pack()

tk.Label(
    root,
    text="Файлы будут переименованы в копию папки. Оригиналы останутся без изменений.",
    fg="gray"
).pack()
progress = ttk.Progressbar(root, orient="horizontal", length=500, mode="determinate")
progress.pack(pady=10)

# --- таблица ---
columns = ("old_name", "new_name", "status")

tree = ttk.Treeview(root, columns=columns, show="headings")

tree.heading("old_name", text="Старое имя")
tree.heading("new_name", text="Новое имя")
tree.heading("status", text="Статус")

tree.pack(fill="both", expand=True)

tree.tag_configure("good", background="#d4edda")        
tree.tag_configure("warn", background="#fff3cd")        
tree.tag_configure("bad", background="#f8d7da") 

# --- запуск приложения ---
root.mainloop()
