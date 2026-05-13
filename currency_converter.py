import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
import os
from datetime import datetime
from threading import Thread

class CurrencyConverter:
    """GUI приложение для конвертации валют"""

    # Бесплатный API ключ (зарегистрируйтесь на https://app.exchangerate-api.com/sign-up)
    # Для тестирования можно использовать демо-ключ, но лучше получить свой
    API_URL = "https://api.exchangerate-api.com/v4/latest/"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Currency Converter")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Данные
        self.currencies = []
        self.exchange_rates = {}
        self.history_file = "history.json"
        self.history = []

        # Загрузка истории
        self.load_history()

        # Создание интерфейса
        self.setup_ui()

        # Загрузка курсов валют при старте
        self.update_currencies()

    def setup_ui(self):
        """Создание интерфейса пользователя"""

        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Настройка весов для растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Заголовок
        title_label = ttk.Label(main_frame, text="Currency Converter",
                                font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # Фрейм для конвертации
        convert_frame = ttk.LabelFrame(main_frame, text="Конвертация", padding="10")
        convert_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        convert_frame.columnconfigure(1, weight=1)

        # Сумма
        ttk.Label(convert_frame, text="Сумма:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(convert_frame, textvariable=self.amount_var, width=20)
        self.amount_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        # Из валюты
        ttk.Label(convert_frame, text="Из валюты:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.from_currency = tk.StringVar()
        self.from_combo = ttk.Combobox(convert_frame, textvariable=self.from_currency, width=20)
        self.from_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # В валюту
        ttk.Label(convert_frame, text="В валюту:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.to_currency = tk.StringVar()
        self.to_combo = ttk.Combobox(convert_frame, textvariable=self.to_currency, width=20)
        self.to_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Кнопка конвертации
        self.convert_btn = ttk.Button(convert_frame, text="Конвертировать",
                                      command=self.convert_currency)
        self.convert_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Результат
        self.result_label = ttk.Label(convert_frame, text="", font=('Arial', 12, 'bold'))
        self.result_label.grid(row=4, column=0, columnspan=2, pady=5)

        # Статус
        self.status_label = ttk.Label(main_frame, text="Готов к работе", foreground="gray")
        self.status_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)

        # Таблица истории
        history_frame = ttk.LabelFrame(main_frame, text="История конвертаций", padding="10")
        history_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        # Создание таблицы
        columns = ("Дата", "Сумма", "Из", "В", "Результат", "Курс")
        self.tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=12)

        # Настройка колонок
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # Полосы прокрутки
        vsb = ttk.Scrollbar(history_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(history_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Размещение таблицы
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Кнопки управления историей
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="Очистить историю",
                  command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Обновить курсы",
                  command=self.update_currencies).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="О программе",
                  command=self.show_about).pack(side=tk.LEFT, padx=5)

        # Загрузка истории в таблицу
        self.refresh_history_table()

        # Привязка клавиши Enter к конвертации
        self.amount_entry.bind('<Return>', lambda event: self.convert_currency())

    def update_currencies(self):
        """Обновление списка валют из API"""
        self.status_label.config(text="Загрузка курсов валют...", foreground="orange")
        self.convert_btn.config(state="disabled")

        # Запуск в отдельном потоке
        thread = Thread(target=self._fetch_currencies)
        thread.daemon = True
        thread.start()

    def _fetch_currencies(self):
        """Получение списка валют из API (в отдельном потоке)"""
        try:
            # Используем USD как базовую валюту для получения списка
            response = requests.get(f"{self.API_URL}USD", timeout=10)
            response.raise_for_status()

            data = response.json()
            self.exchange_rates = data.get("rates", {})
            self.currencies = sorted(self.exchange_rates.keys())

            # Обновление интерфейса в основном потоке
            self.root.after(0, self._update_currency_ui)

        except requests.RequestException as e:
            self.root.after(0, lambda: self._show_error(f"Ошибка загрузки курсов: {str(e)}"))
        except Exception as e:
            self.root.after(0, lambda: self._show_error(f"Неизвестная ошибка: {str(e)}"))

    def _update_currency_ui(self):
        """Обновление UI после загрузки валют"""
        if self.currencies:
            self.from_combo['values'] = self.currencies
            self.to_combo['values'] = self.currencies

            # Установка значений по умолчанию
            if "USD" in self.currencies:
                self.from_currency.set("USD")
            if "EUR" in self.currencies:
                self.to_currency.set("EUR")
            elif len(self.currencies) > 1:
                self.from_currency.set(self.currencies[0])
                self.to_currency.set(self.currencies[1])

            self.status_label.config(text=f"Загружено {len(self.currencies)} валют", foreground="green")
            self.convert_btn.config(state="normal")
        else:
            self.status_label.config(text="Не удалось загрузить валюты", foreground="red")

    def convert_currency(self):
        """Конвертация валюты"""
        # Проверка корректности ввода
        try:
            amount = float(self.amount_var.get().strip())
            if amount <= 0:
                messagebox.showerror("Ошибка", "Сумма должна быть положительным числом!")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Пожалуйста, введите корректную сумму!")
            return

        from_cur = self.from_currency.get()
        to_cur = self.to_currency.get()

        if not from_cur or not to_cur:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите валюты!")
            return

        if from_cur == to_cur:
            result = amount
            rate = 1.0
            self.result_label.config(text=f"{amount:.2f} {from_cur} = {result:.2f} {to_cur}")
        else:
            try:
                # Получение курса
                rate = self.get_exchange_rate(from_cur, to_cur)
                result = amount * rate
                self.result_label.config(text=f"{amount:.2f} {from_cur} = {result:.2f} {to_cur}\nКурс: 1 {from_cur} = {rate:.4f} {to_cur}")

                # Сохранение в историю
                self.save_to_history(amount, from_cur, to_cur, result, rate)

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось получить курс: {str(e)}")
                return

    def get_exchange_rate(self, from_currency, to_currency):
        """Получение курса конвертации"""
        # Если курсы загружены, используем их
        if self.exchange_rates and from_currency in self.exchange_rates and to_currency in self.exchange_rates:
            if from_currency == "USD":
                rate = self.exchange_rates[to_currency]
            else:
                # Конвертация через USD
                usd_rate_from = self.exchange_rates.get(from_currency)
                usd_rate_to = self.exchange_rates.get(to_currency)
                if usd_rate_from and usd_rate_to:
                    rate = usd_rate_to / usd_rate_from
                else:
                    raise Exception("Курс не найден")

            return rate
        else:
            # Прямой запрос к API
            response = requests.get(f"{self.API_URL}{from_currency}", timeout=10)
            response.raise_for_status()
            data = response.json()
            rates = data.get("rates", {})

            if to_currency in rates:
                return rates[to_currency]
            else:
                raise Exception(f"Валюта {to_currency} не найдена")

    def save_to_history(self, amount, from_cur, to_cur, result, rate):
        """Сохранение конвертации в историю"""
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "amount": amount,
            "from_currency": from_cur,
            "to_currency": to_cur,
            "result": result,
            "rate": rate
        }

        self.history.insert(0, record)  # Добавляем в начало

        # Ограничиваем историю 100 записями
        if len(self.history) > 100:
            self.history = self.history[:100]

        # Сохраняем в файл
        self.save_history_to_file()

        # Обновляем таблицу
        self.refresh_history_table()

    def save_history_to_file(self):
        """Сохранение истории в JSON файл"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения истории: {e}")

    def load_history(self):
        """Загрузка истории из JSON файла"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки истории: {e}")
                self.history = []
        else:
            self.history = []

    def refresh_history_table(self):
        """Обновление таблицы истории"""
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Добавляем записи
        for record in self.history:
            self.tree.insert("", "end", values=(
                record.get("date", ""),
                f"{record.get('amount', 0):.2f}",
                record.get("from_currency", ""),
                record.get("to_currency", ""),
                f"{record.get('result', 0):.2f}",
                f"{record.get('rate', 0):.4f}"
            ))

    def clear_history(self):
        """Очистка истории"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите очистить всю историю?"):
            self.history = []
            self.save_history_to_file()
            self.refresh_history_table()
            self.status_label.config(text="История очищена", foreground="orange")
            self.root.after(2000, lambda: self.status_label.config(text="Готов к работе", foreground="gray"))

    def show_about(self):
        """Информация о программе"""
        about_text = """Currency Converter v1.0

Автор: Иван Иванов

Приложение для конвертации валют с использованием
внешнего API exchangerate-api.com

Функции:
- Конвертация между любыми валютами
- Сохранение истории конвертаций
- Автоматическое обновление курсов

Для получения API-ключа:
1. Зарегистрируйтесь на https://app.exchangerate-api.com/sign-up
2. Получите бесплатный ключ
3. Используйте в приложении

Приложение использует API с ограничением 1500 запросов/месяц"""

        messagebox.showinfo("О программе", about_text)

    def _show_error(self, message):
        """Отображение ошибки"""
        self.status_label.config(text=message, foreground="red")
        self.convert_btn.config(state="normal")
        messagebox.showerror("Ошибка", message)

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()


if __name__ == "__main__":
    app = CurrencyConverter()
    app.run()
