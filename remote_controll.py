import ctypes
import random
import subprocess
import sys
from requests.exceptions import ConnectionError
import psutil
import telebot
from telebot import types
import os
import keyboard
import threading
import time
import pyautogui
import win32gui

API_TOKEN = "PASTE HERE YOUR BOT TOKEN"
ADMIN_ID = 1 #Пишем сюда свой айди в тг
FRIEND_ID = 2 #Сюда можно вставить айди друга, который так же будет доступ к боту
bot = telebot.TeleBot(API_TOKEN)

shutdown_timer = None
shutdown_seconds = 0

def safe_send_message(chat_id, text, reply_markup=None, retries=3, delay=2):
	for i in range(retries):
		try:
			return bot.send_message(chat_id, text, reply_markup=reply_markup)
		except ConnectionError:
			if i < retries - 1:
				time.sleep(delay)
			else:
				raise

# === Главное меню ===
def main_menu():
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
	markup.row("🖥️ Свернуть все окна / Развернуть")
	markup.row("⏯️ Пауза видео/музыки")
	markup.row("🔊 Громче", "🔉 Тише")
	if shutdown_timer:
		markup.row("⏲️ Таймер включен")
	else:
		markup.row("⏰ Таймер выключения")
	markup.row("🔄 Перезапустить скрипт")
	markup.row("⚙️ Продвинутый режим")
	return markup


# === Меню таймера ===
def timer_menu():
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
	markup.row("1 час", "2 часа", "Другое", "Сейчас")
	markup.row("⬅️ Назад")
	return markup


@bot.message_handler(commands=['start'])
def start(message):
	if message.from_user.id != ADMIN_ID and message.from_user.id != FRIEND_ID:
		bot.reply_to(message, "⛔ Нет доступа.")
		return
	safe_send_message(message.chat.id, "Привет! 👋 Управление ПК:", reply_markup=main_menu())

def toggle_win_d_api():
	user32 = ctypes.WinDLL('user32')
	user32.keybd_event(0x5B, 0, 0, 0)  # Win down
	user32.keybd_event(0x44, 0, 0, 0)  # D down
	user32.keybd_event(0x44, 0, 2, 0)  # D up
	user32.keybd_event(0x5B, 0, 2, 0)  # Win up

@bot.message_handler(func=lambda m: m.text == "🖥️ Свернуть все окна / Развернуть")
def minimize_all(message):
	# pyautogui.hotkey('win', 'd')
	toggle_win_d_api()
	safe_send_message(message.chat.id, "🔳 Свернул или развернул окна.")


@bot.message_handler(func=lambda m: m.text == "⏯️ Пауза видео/музыки")
def pause_media(message):
	keyboard.send("play/pause media")
	safe_send_message(message.chat.id, "⏸️ Пауза/воспроизведение.")


@bot.message_handler(func=lambda m: m.text == "🔊 Громче")
def volume_up(message):
	keyboard.send("volume up")


@bot.message_handler(func=lambda m: m.text == "🔉 Тише")
def volume_down(message):
	keyboard.send("volume down")


@bot.message_handler(func=lambda m: m.text in ["⏰ Таймер выключения", "⏲️ Таймер включен"])
def timer(message):
	global shutdown_timer
	if shutdown_timer:
		safe_send_message(
			message.chat.id,
			f"⏲️ Таймер уже включен. Выключение через {shutdown_seconds} сек.",
			reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🛑 Остановить таймер").add("⬅️ Назад")
		)
	else:
		safe_send_message(message.chat.id, "Выбери время:", reply_markup=timer_menu())


@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def back_to_main(message):
	safe_send_message(message.chat.id, "Главное меню:", reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == "1 час")
def timer_1h(message):
	set_shutdown_timer(message, 3600)


@bot.message_handler(func=lambda m: m.text == "2 часа")
def timer_2h(message):
	set_shutdown_timer(message, 7200)


@bot.message_handler(func=lambda m: m.text == "Другое")
def timer_other(message):
	safe_send_message(message.chat.id, "Введите время в секундах:")
	bot.register_next_step_handler(message, custom_timer)


def custom_timer(message):
	try:
		seconds = int(message.text)
		set_shutdown_timer(message, seconds)
	except ValueError:
		safe_send_message(message.chat.id, "❌ Введи число секунд.", reply_markup=timer_menu())


def set_shutdown_timer(message, seconds):
	global shutdown_timer, shutdown_seconds
	if shutdown_timer:
		safe_send_message(message.chat.id, "❗ Таймер уже включен.")
		return

	shutdown_seconds = seconds
	os.system(f"shutdown -s -t {seconds}")
	safe_send_message(
		message.chat.id,
		f"✅ Компьютер выключится через {seconds} сек.",
		reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🛑 Остановить таймер").add("⬅️ Назад")
	)

	shutdown_timer = threading.Thread(target=shutdown_countdown, args=(message,), daemon=True)
	shutdown_timer.start()


def shutdown_countdown(message=None):
	global shutdown_timer, shutdown_seconds
	while shutdown_seconds > 0:
		time.sleep(1)
		shutdown_seconds -= 1
		if shutdown_seconds == 1 and message:
			safe_send_message(message.chat.id, "💤 Выключаю компьютер...")
	shutdown_timer = None


@bot.message_handler(func=lambda m: m.text == "Сейчас")
def shutdown_now(message):
	markup = types.InlineKeyboardMarkup()
	markup.row(
		types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_shutdown"),
		types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_shutdown")
	)
	safe_send_message(message.chat.id, "Подтвердите:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_shutdown", "cancel_shutdown"])
def confirm_shutdown(call):
	if call.data == "confirm_shutdown":
		bot.edit_message_text("💤 Выключаю компьютер...", call.message.chat.id, call.message.message_id)
		subprocess.Popen(['cmd.exe', '/k', 'color 0A & cd /d C:\\ & dir /s'], cwd='C:\\',creationflags=subprocess.CREATE_NEW_CONSOLE)
		time.sleep(2.2)
		os.system("shutdown -s -t 1")
	else:
		bot.edit_message_text("❌ Отменено.", call.message.chat.id, call.message.message_id)


@bot.message_handler(func=lambda m: m.text == "🛑 Остановить таймер")
def stop_timer(message):
	global shutdown_timer, shutdown_seconds
	os.system("shutdown -a")
	shutdown_timer = None
	shutdown_seconds = 0
	safe_send_message(message.chat.id, "❌ Таймер остановлен.", reply_markup=main_menu())


@bot.message_handler(func=lambda m: m.text == "🔄 Перезапустить скрипт")
def restart_script_confirm(message):
	markup = types.InlineKeyboardMarkup()
	markup.row(
		types.InlineKeyboardButton("✅ Перезапустить", callback_data="confirm_restart"),
		types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_restart")
	)
	bot.send_message(message.chat.id, "Вы уверены, что хотите перезапустить скрипт?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["confirm_restart", "cancel_restart"])
def restart_script_callback(call):
	if call.data == "confirm_restart":
		bot.edit_message_text("♻️ Перезапуск...", call.message.chat.id, call.message.message_id)
		threading.Thread(target=_restart, daemon=True).start()
	else:
		bot.edit_message_text("❌ Перезапуск отменён.", call.message.chat.id, call.message.message_id)

def _restart():
	python = sys.executable
	script = sys.argv[0]
	subprocess.Popen([python, script])
	os._exit(0)  # завершает текущий процесс

# === Продвинутый режим ===
@bot.message_handler(func=lambda m: m.text == "⚙️ Продвинутый режим")
def advanced_mode(message):
	markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
	markup.row("📸 Снимок экрана")
	markup.row("🚀 Запуск / Остановка приложений")
	markup.row("⬅️ Назад")
	safe_send_message(message.chat.id, "Продвинутый режим:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📸 Снимок экрана")
def screenshot(message):
	import tempfile
	from datetime import datetime

	status = safe_send_message(message.chat.id, "📷 Фотографирую...")
	try:
		shot_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		# создаём временный файл
		with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
			screenshot_path = tmp_file.name

		# делаем скриншот
		pyautogui.screenshot(screenshot_path)
	except Exception as e:
		safe_send_message(message.chat.id, f"❌ Ошибка при создании скриншота:\n{e}")
		print("Ошибка при создании скриншота:", e)
	# получаем активное окно
	try:
		active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
		if not active_window:
			active_window = "Не определено"
	except Exception:
		active_window = "Не удалось получить"
	try:
		def enum_windows(hwnd, result):
			if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
				result.append(win32gui.GetWindowText(hwnd))
			return True
		windows = []
		win32gui.EnumWindows(enum_windows, windows)
		windows = [w for w in windows if not any(x in w.lower() for x in ["taskmgr", "settings", "program manager"])]
		windows_list = "\n• ".join(windows[:10]) + ("\n..." if len(windows) > 10 else "")
		if not windows_list:
			windows_list = "Нет открытых окон."

		caption = (
			"📸 <b>Снимок сделан</b>\n"
			"━━━━━━━━━━━━━━━\n\n"
			f"🕒 <b>Время съёмки:</b> <code>{shot_time}</code>\n\n"
			f"🪟 <b>Активное окно:</b> <code>{active_window}</code>\n\n"
			f"📋 <b>Открытые окна:</b>\n• {windows_list}\n\n"
			"━━━━━━━━━━━━━━━"
		)

		with open(screenshot_path, "rb") as photo:
			bot.edit_message_media(
				chat_id=message.chat.id,
				message_id=status.message_id,
				media=types.InputMediaPhoto(photo, caption=caption, parse_mode="HTML")
			)
	except Exception as e:
		safe_send_message(message.chat.id, f"❌ Ошибка при создании скриншота:\n{e}")
		print("Ошибка при создании скриншота:", e)
	try:
		os.remove(screenshot_path)
	except Exception:
		pass

@bot.message_handler(func=lambda m: m.text == "🚀 Запуск / Остановка приложений")
def manage_apps(message):
	app_menu(message)

app_status_message = {}
app_status_state = {}
def start_app_monitor(message):
	chat_id = message.chat.id

	# инициализация состояния
	discord_running = is_process_running("Discord.exe")
	r6_running = is_process_running("RainbowSix.exe")
	app_status_state[chat_id] = (discord_running, r6_running)

	if chat_id not in app_status_message:
		markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
		markup.row(f"💬 Discord [{'X' if discord_running else '+'}]")
		markup.row(f"🎮 R6 Siege [{'X' if r6_running else '+'}]")
		markup.row("⬅️ Назад")
		sent_msg = safe_send_message(chat_id, "Выберите приложение:", reply_markup=markup)
		app_status_message[chat_id] = sent_msg.message_id

	def monitor():
		while True:
			# если пользователь ушёл из меню — прекращаем мониторинг
			if chat_id not in app_status_state:
				break

			discord_running_new = is_process_running("Discord.exe")
			r6_running_new = is_process_running("RainbowSix.exe")

			old_discord, old_r6 = app_status_state[chat_id]

			# если что-то изменилось — обновляем клавиатуру
			if (discord_running_new != old_discord) or (r6_running_new != old_r6):
				bot.delete_message(chat_id, app_status_message[chat_id])

				# создаём новую клавиатуру
				markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
				markup.row(f"💬 Discord [{'X' if discord_running_new else '+'}]")
				markup.row(f"🎮 R6 Siege [{'X' if r6_running_new else '+'}]")
				print(f"🎮 R6 Siege [{'X' if r6_running else '+'}]")
				markup.row("⬅️ Назад")

				sent_msg = safe_send_message(chat_id, "Выберите приложение:", reply_markup=markup)
				app_status_message[chat_id] = sent_msg.message_id
				app_status_state[chat_id] = (discord_running_new, r6_running_new)
			time.sleep(1)  # проверяем каждую секунду
	threading.Thread(target=monitor, daemon=True).start()

def app_menu(message):
	discord_running = is_process_running("Discord.exe")
	r6_running = is_process_running("RainbowSix.exe")

	markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
	markup.row(f"💬 Discord [{'X' if discord_running else '+'}]")
	markup.row(f"🎮 R6 Siege [{'X' if r6_running else '+'}]")
	markup.row("⬅️ Назад")

	sent_msg = safe_send_message(message.chat.id, "Выберите приложение:", reply_markup=markup)
	app_status_message[message.chat.id] = sent_msg.message_id

	# запускаем поток мониторинга
	start_app_monitor(message)

def is_process_running(process_name):
	for proc in psutil.process_iter(['name']):
		if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
			return True
	return False

@bot.message_handler(func=lambda m: m.text.startswith("💬 Discord"))
def toggle_discord(message):
	app_name = "Discord"
	process = "Discord.exe"
	path = r"C:\Users\Santik\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Discord Inc\Discord.lnk"
	toggle_app(message, app_name, process, path)


@bot.message_handler(func=lambda m: m.text.startswith("🎮 R6 Siege"))
def toggle_r6(message):
	app_name = "R6 Siege"
	process = "RainbowSix.exe"
	path = r"C:\Users\Santik\Desktop\Software\Ярлыки\R6 Siege.url"
	toggle_app(message, app_name, process, path)


def toggle_app(message, app_name, process_name, app_path):
	def kill_processes():
		killed_any = False
		for proc in psutil.process_iter(['name']):
			if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
				try:
					proc.terminate()
					killed_any = True
				except Exception as e:
					print(f"Ошибка при завершении {process_name}: {e}")
		return killed_any

	if is_process_running(process_name):
		trying = safe_send_message(message.chat.id, f"🔄 Пытаюсь закрыть {app_name}...")
		start_time = time.time()
		while is_process_running(process_name):
			kill_processes()
			time.sleep(1.5)

			if not is_process_running(process_name):
				bot.edit_message_text(f"✅ {app_name} закрыт.", chat_id=message.chat.id, message_id=trying.message_id)
				break

			if time.time() - start_time > 10:
				bot.edit_message_text(f"⚠️ Не удалось закрыть {app_name} за 10 секунд.", message.chat.id, trying.message_id)
				break
	else:
		try:
			if app_name == "R6 Siege":
				subprocess.run(["schtasks", "/run", "/tn", "RunSiege"], encoding="cp866")
				safe_send_message(message.chat.id, f"🚀 {app_name} запущен.")
			else:
				os.startfile(app_path)
				safe_send_message(message.chat.id, f"🚀 {app_name} запущен.")
		except Exception as e:
			safe_send_message(message.chat.id, f"⚠️ Не удалось запустить {app_name}: {e}")

	time.sleep(1)
	# app_menu(message)

print("✅ Бот запущен.")
bot.infinity_polling()

