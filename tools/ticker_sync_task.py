import sqlite3
import aiohttp
import asyncio
import os
import okx.MarketData as MarketData
import toml

# 定义数据库文件路径
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sqlite_db')  # 上一级目录的 sqlite_db 文件夹
DB_FILE = os.path.join(DB_DIR, 'ticker_data.db')

# 确保 data_dir 文件夹存在
os.makedirs(DB_DIR, exist_ok=True)

def create_table():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ticker_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inst_id TEXT,             -- 币种, 如BTC/ETH
            type TEXT,                -- 类型 SPOT = 现货, SWAP = 合约
            date DATE,                -- 交易日
            close_price REAL,         -- 收盘价
            high_price REAL,          -- 最高价
            low_price REAL,           -- 最低价
            increase REAL             -- 涨幅(负值表示跌幅), 以百分比表示，如 20 表示 涨20%
            volCcyQuote REAL          -- 交易量(USDT为单位)
        )
    ''')

    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_inst ON ticker_data (inst_id);
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_date ON ticker_data (date);
    ''')

    conn.commit()
    conn.close()



api_key = ''
secret = ''
passphrase = ''
flag = 0

def load_config(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        config_data = toml.load(file)
        api_key=config_data['api']['key']
        secret=config_data['api']['secret']
        passphase=config_data['api']['passphase']
# 异步获取行情数据
async def fetch_ticker_data(session, inst_id):
    marketApi = MarketData.MarketAPI(api_key, secret, passphrase, False, flag)
    marketApi.get_history_candlesticks(instId=inst_id)

    url = f'https://api.example.com/stock/{inst_id}'
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                print(f"Failed to fetch data for {inst_id}: HTTP {response.status}")
                return None
    except Exception as e:
        print(f"Error fetching data for {inst_id}: {e}")
        return None

# 异步写入股票数据到数据库
async def insert_ticker_data(ticker_data):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ticker_data (inst_id, date, close_price, high_price, low_price, increase)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        ticker_data['inst_id'],
        ticker_data['date'],
        ticker_data['close_price'],
        ticker_data['high_price'],
        ticker_data['low_price'],
        ticker_data['increase']
    ))
    conn.commit()
    conn.close()

# 异步主函数
async def main():
    # 创建表（如果不存在）
    create_table()

    # 假设有一个包含所有股票代码的列表
    stock_list = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']

    # 创建 aiohttp 会话
    async with aiohttp.ClientSession() as session:
        tasks = []
        for inst_id in stock_list:
            # 创建异步任务
            task = asyncio.create_task(fetch_and_save_data(session, inst_id))
            tasks.append(task)

        # 等待所有任务完成
        await asyncio.gather(*tasks)


async def fetch_and_save_data(session, inst_id):
    ticker_data = await fetch_ticker_data(session, inst_id)
    if ticker_data:
        print(f"Inserting data for {inst_id}: {ticker_data}")
        await insert_ticker_data(ticker_data)
    else:
        print(f"No data found for {inst_id}")



if __name__ == '__main__':
    asyncio.run(main())