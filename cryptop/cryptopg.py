import pygcurse
import pygame
from pygame.locals import *
import os
import sys
import re
import shutil
import configparser
import json
import pkg_resources

import requests
import requests_cache

# GLOBALS!
WINDOW_WIDTH = 80
WINDOW_HEIGHT = 25
BASEDIR = os.path.join(os.path.expanduser('~'), '.cryptop')
DATAFILE = os.path.join(BASEDIR, 'wallet.json')
CONFFILE = os.path.join(BASEDIR, 'config.ini')
CONFIG = configparser.ConfigParser()
COIN_FORMAT = re.compile('[A-Z]{2,5},\d{0,}\.?\d{0,}')

KEY_ESCAPE = 27
KEY_ZERO = 48
KEY_A = 65
KEY_Q = 81
KEY_R = 82
KEY_a = 97
KEY_q = 113
KEY_r = 114


def read_configuration(confpath):
	# copy our default config file
	if not os.path.isfile(confpath):
		defaultconf = pkg_resources.resource_filename(__name__, 'config.ini')
		shutil.copyfile(defaultconf, CONFFILE)

	CONFIG.read(confpath)
	return CONFIG


def if_coin(coin, url='https://www.cryptocompare.com/api/data/coinlist/'):
	'''Check if coin exists'''
	return coin in requests.get(url).json()['Data']


def get_price(coin, curr=None):
	'''Get the data on coins'''
	curr = curr or CONFIG['api'].get('currency', 'USD')
	fmt = 'https://min-api.cryptocompare.com/data/pricemultifull?fsyms={}&tsyms={}'

	try:
		r = requests.get(fmt.format(coin, curr))
	except requests.exceptions.RequestException:
		sys.exit('Could not complete request')

	try:
		data_raw = r.json()['RAW']
		return [(data_raw[c][curr]['PRICE'],
				data_raw[c][curr]['HIGH24HOUR'],
				data_raw[c][curr]['LOW24HOUR']) for c in coin.split(',')]
	except:
		sys.exit('Could not parse data')


def get_theme_colors():
	''' Returns curses colors according to the config'''
	def get_curses_color(name_or_value):
		try:
			return getattr(curses, 'COLOR_' + name_or_value.upper())
		except AttributeError:
			return int(name_or_value)

	theme_config = CONFIG['theme']
	return (get_curses_color(theme_config.get('text', 'yellow')),
		get_curses_color(theme_config.get('banner', 'yellow')),
		get_curses_color(theme_config.get('banner_text', 'black')),
		get_curses_color(theme_config.get('background', -1)))


def conf_scr():
	'''Configure the screen and colors/etc'''
	# curses.curs_set(0)
	# curses.start_color()
	# curses.use_default_colors()
	# text, banner, banner_text, background = get_theme_colors()
	# curses.init_pair(2, text, background)
	# curses.init_pair(3, banner_text, banner)
	# curses.halfdelay(10)


def write_scr(win, wallet, y, x):
	'''Write text and formatting to screen'''
	if y >= 1:
		win.cursor = 0, 0
		win.write('cryptop v2.0')
	if y >= 2:
		header = '  COIN      PRICE          HELD        VAL     HIGH      LOW  '
		win.cursor = 0, 1
		win.write(header)

	total = 0
	coinl = list(wallet.keys())
	heldl = list(wallet.values())
	if coinl:
		coinvl = get_price(','.join(coinl))

		if y > 3:
			for coin, val, held in zip(coinl, coinvl, heldl):
				if coinl.index(coin) + 2 < y:
					win.cursor = coinl.index(coin) + 2, 0
					win.write('  {:<5}  {:8.2f} {:>13.8f} {:10.2f} {:8.2f} {:8.2f}'.format(coin, val[0], float(held), float(held) * val[0],	val[1], val[2]))
				total += float(held) * val[0]

	if y > len(coinl) + 3:
		win.cursor = 0, y - 2
		win.write('Total Holdings: {:10.2f}    '.format(total))
		win.cursor = 0, y - 1
		win.write('[A] Add coin or update value [R] Remove coin [0\Q]Exit')


def read_wallet():
	''' Reads the wallet data from its json file '''
	try:
		with open(DATAFILE, 'r') as f:
			return json.load(f)
	except (FileNotFoundError, ValueError):
		# missing or malformed wallet
		write_wallet({})
		return {}


def write_wallet(wallet):
	''' Reads the wallet data to its json file '''
	with open(DATAFILE, 'w') as f:
		json.dump(wallet, f)


def get_string(stdscr, prompt):
	'''Requests and string from the user'''
	curses.echo()
	stdscr.clear()
	stdscr.addnstr(0, 0, prompt, -1, curses.color_pair(2))
	curses.curs_set(1)
	stdscr.refresh()
	in_str = stdscr.getstr(1, 0, 20).decode()
	curses.noecho()
	curses.curs_set(0)
	stdscr.clear()
	curses.halfdelay(10)
	return in_str


def add_coin(coin_amount, wallet):
	''' Remove a coin and its amount to the wallet '''
	coin_amount = coin_amount.upper()
	if not COIN_FORMAT.match(coin_amount):
		return wallet

	coin, amount = coin_amount.split(',')
	wallet[coin] = amount

	return wallet


def remove_coin(coin, wallet):
	''' Remove a coin and its amount from the wallet '''
	# coin = '' if window is resized while waiting for string
	if coin:
		coin = coin.upper()
		wallet.pop(coin, None)
	return wallet


def terminal_loop():
	win = pygcurse.PygcurseWindow(WINDOW_WIDTH, WINDOW_HEIGHT)
	win.autoblit = False
	inp = 0
	wallet = read_wallet()
	x, y = 	WINDOW_WIDTH, WINDOW_HEIGHT
	conf_scr()
	# stdscr.bkgd(' ', curses.color_pair(2))
	# stdscr.clear()
	#stdscr.nodelay(1)
	# while inp != 48 and inp != 27 and inp != 81 and inp != 113:
	while True:
		for event in pygame.event.get():  # the event loop
			if event.type == QUIT or event.type == KEYDOWN and event.key in (K_ESCAPE, K_q):
				pygame.quit()
				sys.exit()

			try:
				write_scr(win, wallet, y, x)
				win.blittowindow()
			except RuntimeError:
				pass

			if event.type == KEYDOWN:
				isWalletChanged = False
				if event.key == K_a:
#           if y > 2:
					data = win.input('Enter in format Symbol,Amount e.g. BTC,10')
					wallet = add_coin(data, wallet)
					isWalletChanged = True
				elif event.key == K_r:
#	if y > 2:
					data = win.input('Enter the symbol of coin to be removed, e.g. BTC')
					wallet = remove_coin(data, wallet)
					isWalletChanged = True

				if isWalletChanged:
					write_wallet(wallet)


def main():
	if os.path.isfile(BASEDIR):
		sys.exit('Please remove your old configuration file at {}'.format(BASEDIR))
	os.makedirs(BASEDIR, exist_ok=True)

	global CONFIG
	CONFIG = read_configuration(CONFFILE)

	requests_cache.install_cache(cache_name='api_cache', backend='memory',
		expire_after=int(CONFIG['api'].get('cache', 10)))

	terminal_loop()


if __name__ == "__main__":
	main()
