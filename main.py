import tkinter as tk
from tkinter import ttk
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageTk
import io
import time
from datetime import datetime, timedelta


class CryptoWidget:
    def __init__(self, root):
        self.root = root
        self.images = {}
        self.graph_windows = {}
        self.last_api_call = 0
        self.setup_ui()
        self.update_widget()

    def setup_ui(self):
        self.root.title("Crypto Market Widget")
        self.root.geometry("500x400")

        # Set dark background
        bg_color = "#1e1e1e"
        fg_color = "#dcdcdc"

        self.root.configure(bg=bg_color)

        self.frame = tk.Frame(self.root, bg=bg_color)
        self.frame.pack(padx=10, pady=10)

        self.status_label = tk.Label(self.root, text="Initializing...", bg=bg_color, fg="lightgreen")
        self.status_label.pack()

        # Table setup
        self.columns = ("Pair", "Price", "24h Change", "7d Change", "24h Volume", "View Graph")
        self.table = ttk.Treeview(self.frame, columns=self.columns, show="headings", height=12)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=bg_color,
                        foreground=fg_color,
                        fieldbackground=bg_color,
                        rowheight=25,
                        font=('Arial', 10))
        style.configure("Treeview.Heading",
                        background="#333333",
                        foreground="white",
                        font=('Arial', 10, 'bold'))

        for col in self.columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=80, anchor='center')

        self.coins_list = ['bitcoin', 'ethereum', 'solana', 'dogecoin',
                           'ripple', 'binancecoin', 'litecoin']

        for coin in self.coins_list:
            self.table.insert("", "end", iid=coin, values=(coin.upper(), "Loading...", "", "", "", "View"))

        # Add both ETH/BTC and BTC/ETH pairs
        self.table.insert("", "end", iid="eth_btc", values=("ETH/BTC", "Loading...", "", "", "", "View"))
        self.table.insert("", "end", iid="btc_eth", values=("BTC/ETH", "Loading...", "", "", "", "View"))
        self.table.insert("", "end", iid="eur_usd", values=("EUR/USD", "Loading...", "", "", "", "View"))
        self.table.pack()


        # Add button click event
        self.table.bind("<ButtonRelease-1>", self.on_table_click)

    def fetch_exchange_rates(self):
        try:
            url = "https://open.er-api.com/v6/latest/EUR"
            response = requests.get(url, timeout=10)
            data = response.json()

            if data.get("result") == "success":
                usd_value = data["rates"].get("USD")
                # Fake a 7-day history with the same value (for now)
                history = [usd_value] * 7 if usd_value else []
                return usd_value, history
            else:
                self.update_status("No FX data available", "red")
                return None, []
        except Exception as e:
            self.update_status(f"FX API Exception: {str(e)}", "red")
            return None, []

    def on_table_click(self, event):
        region = self.table.identify("region", event.x, event.y)
        if region == "cell":
            column = self.table.identify_column(event.x)
            if column == "#6":
                item = self.table.identify_row(event.y)
                if item in self.images:
                    self.show_graph_window(item)

    def show_graph_window(self, coin_id):
        if coin_id in self.graph_windows:
            try:
                self.graph_windows[coin_id]['window'].destroy()
            except:
                pass

        window = tk.Toplevel(self.root)
        window.title(f"{coin_id.upper()} Price Trend")
        window.geometry("600x400")

        canvas = tk.Canvas(window, width=580, height=380, bg='white')
        canvas.pack(pady=20)

        image = self.images.get(coin_id)
        if image:
            canvas.image = image
            canvas.create_image(275, 175, image=image)

        self.graph_windows[coin_id] = {
            'window': window,
            'canvas': canvas,
            'image': image
        }

    def fetch_data(self):
        try:
            current_time = time.time()
            if current_time - self.last_api_call < 10:
                time.sleep(10 - (current_time - self.last_api_call))

            self.last_api_call = time.time()

            url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                'vs_currency': 'usd',
                'ids': ','.join(self.coins_list),
                'price_change_percentage': '24h,7d'
            }

            response = requests.get(url, params=params, timeout=15)
            self.update_status(f"Last update: {datetime.now().strftime('%H:%M:%S')}","white")

            if response.status_code == 429:
                self.update_status("Rate limited - waiting 60 seconds", "red")
                return None

            if response.status_code != 200:
                self.update_status(f"API Error: {response.status_code}", "red")
                return None

            data = response.json()
            coins = {}

            for coin in data:
                coin_id = coin['id']
                coins[coin_id] = {
                    'price': coin['current_price'],
                    'change_24h': coin.get('price_change_percentage_24h', 0),
                    'change_7d': coin.get('price_change_percentage_7d_in_currency', 0),
                    'volume': coin['total_volume'],
                    'prices_7d': []
                }

            for coin_id in coins:
                time.sleep(2)
                history_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
                history_params = {'vs_currency': 'usd', 'days': '7'}

                try:
                    history_response = requests.get(history_url, params=history_params, timeout=15)
                    history_data = history_response.json()
                    coins[coin_id]['prices_7d'] = [price[1] for price in history_data.get('prices', [])]
                except Exception as e:
                    print(f"Error fetching history for {coin_id}: {e}")
                    coins[coin_id]['prices_7d'] = [coins[coin_id]['price']] * 7

            if 'ethereum' in coins and 'bitcoin' in coins:
                eth_history = coins['ethereum']['prices_7d']
                btc_history = coins['bitcoin']['prices_7d']
                min_len = min(len(eth_history), len(btc_history))

                eth_btc_history = [e / b for e, b in zip(eth_history[:min_len], btc_history[:min_len])]
                btc_eth_history = [b / e for e, b in zip(eth_history[:min_len], btc_history[:min_len])]

                coins['eth_btc'] = {
                    'price': coins['ethereum']['price'] / coins['bitcoin']['price'],
                    'change_24h': None,
                    'change_7d': None,
                    'prices_7d': eth_btc_history
                }

                coins['btc_eth'] = {
                    'price': coins['bitcoin']['price'] / coins['ethereum']['price'],
                    'change_24h': None,
                    'change_7d': None,
                    'prices_7d': btc_eth_history
                }

            return coins

        except Exception as e:
            self.update_status(f"API Error: {str(e)}", "red")
            return None

    def create_graph(self, coin_id, prices_7d):
        if len(prices_7d) > 1:
            plt.figure(figsize=(6, 4))
            plt.plot(prices_7d, color='blue', linewidth=2)
            plt.title(f'{coin_id.upper()} 7-Day Price Trend', fontsize=12, pad=20)
            plt.xlabel('Hours', fontsize=10)
            plt.ylabel('Price', fontsize=10)
            plt.grid(True, linestyle='--', alpha=0.7)

            current_price = prices_7d[-1]
            plt.annotate(f'Current: {current_price:.6f}',
                         xy=(6, current_price),
                         xytext=(5, current_price * 0.95),
                         arrowprops=dict(facecolor='black', shrink=0.05),
                         bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5))

            plt.tight_layout()

            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()

            img = Image.open(buf)
            img = ImageTk.PhotoImage(img)
            return img
        return None

    def update_widget(self):
        data = self.fetch_data()

        if data:
            for coin_id in self.coins_list:
                if coin_id in data:
                    coin_data = data[coin_id]
                    name = coin_id.upper()
                    price = f"${coin_data['price']:,.2f}"
                    change_24h = f"{coin_data['change_24h']:.2f}%"
                    change_7d = f"{coin_data['change_7d']:.2f}%"
                    volume = f"${coin_data['volume'] / 1e9:.2f}B" if coin_data['volume'] >= 1e9 else f"${coin_data['volume'] / 1e6:.2f}M"

                    self.table.item(coin_id, values=(name, price, change_24h, change_7d, volume, "View"))
                    graph_image = self.create_graph(coin_id, coin_data['prices_7d'])
                    if graph_image:
                        self.images[coin_id] = graph_image

                        if coin_id in self.graph_windows:
                            graph_ref = self.graph_windows[coin_id]
                            canvas = graph_ref['canvas']
                            canvas.image = graph_image
                            canvas.delete("all")
                            canvas.create_image(275, 175, image=graph_image)
                            graph_ref['image'] = graph_image

            for pair in ['eth_btc', 'btc_eth']:
                if pair in data:
                    price = f"{data[pair]['price']:.6f}"
                    self.table.item(pair, values=(pair.upper(), price, "", "", "", "View"))
                    graph_image = self.create_graph(pair, data[pair]['prices_7d'])
                    if graph_image:
                        self.images[pair] = graph_image
                        if pair in self.graph_windows:
                            graph_ref = self.graph_windows[pair]
                            canvas = graph_ref['canvas']
                            canvas.image = graph_image
                            canvas.delete("all")
                            canvas.create_image(275, 175, image=graph_image)
                            graph_ref['image'] = graph_image

            # EUR/USD update
            if not hasattr(self, 'last_fx_call') or time.time() - self.last_fx_call > 300:
                self.eur_usd_value, self.eur_usd_history = self.fetch_exchange_rates()
                self.last_fx_call = time.time()

            if self.eur_usd_value:
                price = f"{self.eur_usd_value:.4f}"
                self.table.item('eur_usd', values=("EUR/USD", price, "", "", "", "View"))
                graph_image = self.create_graph('eur_usd', self.eur_usd_history)
                if graph_image:
                    self.images['eur_usd'] = graph_image
                    if 'eur_usd' in self.graph_windows:
                        graph_ref = self.graph_windows['eur_usd']
                        canvas = graph_ref['canvas']
                        canvas.image = graph_image
                        canvas.delete("all")
                        canvas.create_image(275, 175, image=graph_image)
                        graph_ref['image'] = graph_image

        self.root.after(60000, self.update_widget)

    def update_status(self, message, color="black"):
        self.status_label.config(text=message, fg=color)


if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoWidget(root)
    root.mainloop()
