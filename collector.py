"""
Deribit Options Data Collector

Real-time cryptocurrency options data collector for Deribit exchange.
Collects prices, Greeks, implied volatility, and market data.

Author: Kirill-Miroshnichenko
License: MIT
"""

import requests
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
import pyarrow.parquet as pq
import pyarrow as pa


class DeribitDataCollector:
    """Class for collecting options data from Deribit"""
    
    def __init__(self, currency='BTC', data_dir='deribit_data'):
        """
        Initialize the collector
        
        Args:
            currency (str): 'BTC' or 'ETH'
            data_dir (str): directory for storing data
        """
        self.base_url = 'https://www.deribit.com/api/v2/public'
        self.currency = currency
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        print(f"Initialized collector for {currency}")
        print(f"Data directory: {self.data_dir.absolute()}")
    
    def get_instruments(self, kind='option', expired=False):
        """
        Get list of all instruments
        
        Args:
            kind (str): instrument type ('option', 'future')
            expired (bool): include expired instruments
            
        Returns:
            list: list of instruments
        """
        url = f'{self.base_url}/get_instruments'
        params = {
            'currency': self.currency,
            'kind': kind,
            'expired': 'false' if not expired else 'true'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()['result']
        except Exception as e:
            print(f"Error fetching instruments: {e}")
            return []
    
    def get_orderbook(self, instrument_name):
        """
        Get orderbook for instrument
        
        Args:
            instrument_name (str): instrument name
            
        Returns:
            dict: orderbook data or None
        """
        url = f'{self.base_url}/get_order_book'
        params = {'instrument_name': instrument_name}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()['result']
        except Exception as e:
            print(f"Error for {instrument_name}: {e}")
            return None
    
    def collect_options_data(self):
        """
        Collect data for all options
        
        Returns:
            pd.DataFrame: DataFrame with collected data
        """
        print(f"Starting data collection for {self.currency}...")
        
        # Get list of all options
        instruments = self.get_instruments()
        print(f"Found instruments: {len(instruments)}")
        
        data = []
        
        for idx, instrument in enumerate(instruments):
            instrument_name = instrument['instrument_name']
            
            # Get orderbook data (contains greeks and prices)
            orderbook = self.get_orderbook(instrument_name)
            
            if orderbook:
                record = {
                    'timestamp': datetime.now(),
                    'instrument_name': instrument_name,
                    'expiration_timestamp': instrument['expiration_timestamp'],
                    'strike': instrument['strike'],
                    'option_type': instrument['option_type'],
                    
                    # Prices
                    'mark_price': orderbook.get('mark_price'),
                    'last_price': orderbook.get('last_price'),
                    'bid_price': orderbook['best_bid_price'] if orderbook.get('best_bid_price') else None,
                    'ask_price': orderbook['best_ask_price'] if orderbook.get('best_ask_price') else None,
                    'mid_price': (orderbook.get('best_bid_price', 0) + orderbook.get('best_ask_price', 0)) / 2 if orderbook.get('best_bid_price') and orderbook.get('best_ask_price') else None,
                    
                    # Greeks
                    'delta': orderbook.get('greeks', {}).get('delta'),
                    'gamma': orderbook.get('greeks', {}).get('gamma'),
                    'vega': orderbook.get('greeks', {}).get('vega'),
                    'theta': orderbook.get('greeks', {}).get('theta'),
                    'rho': orderbook.get('greeks', {}).get('rho'),
                    
                    # Volatility
                    'mark_iv': orderbook.get('mark_iv'),
                    'bid_iv': orderbook.get('bid_iv'),
                    'ask_iv': orderbook.get('ask_iv'),
                    
                    # Volume
                    'open_interest': orderbook.get('open_interest'),
                    'volume_24h': orderbook.get('stats', {}).get('volume'),
                    
                    # Underlying
                    'underlying_price': orderbook.get('underlying_price'),
                    'underlying_index': orderbook.get('underlying_index')
                }
                
                data.append(record)
            
            # Small delay to avoid rate limit
            if (idx + 1) % 10 == 0:
                print(f"Processed: {idx + 1}/{len(instruments)}")
                time.sleep(0.5)
        
        df = pd.DataFrame(data)
        print(f"\nDone! Collected records: {len(df)}")
        
        return df
    
    def get_daily_filename(self, date=None):
        """
        Get filename for specific date
        
        Args:
            date (datetime): date (default today)
            
        Returns:
            Path: file path
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y%m%d')
        return self.data_dir / f'{self.currency}_options_{date_str}.parquet'
    
    def save_to_parquet(self, df):
        """
        Save data to Parquet (append to current day file)
        
        Args:
            df (pd.DataFrame): data to save
            
        Returns:
            Path: path to saved file
        """
        if df.empty:
            print("No data to save")
            return None
        
        filename = self.get_daily_filename()
        
        # If file for today exists - append
        if filename.exists():
            existing_df = pd.read_parquet(filename)
            df = pd.concat([existing_df, df], ignore_index=True)
            print(f"Appended to existing file: {filename}")
        else:
            print(f"Created new file: {filename}")
        
        # Save with compression
        df.to_parquet(filename, compression='snappy', index=False)
        print(f"Total records in file: {len(df)}")
        
        return filename
    
    def load_data(self, start_date=None, end_date=None):
        """
        Load data for period
        
        Args:
            start_date (datetime): start of period (None = all files)
            end_date (datetime): end of period (None = all files)
            
        Returns:
            pd.DataFrame: combined data
        """
        files = sorted(self.data_dir.glob(f'{self.currency}_options_*.parquet'))
        
        if not files:
            print("No saved data found")
            return pd.DataFrame()
        
        dfs = []
        
        for file in files:
            # Filter by dates if needed
            if start_date or end_date:
                file_date = datetime.strptime(file.stem.split('_')[-1], '%Y%m%d')
                
                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue
            
            df = pd.read_parquet(file)
            dfs.append(df)
            print(f"Loaded: {file.name} ({len(df)} records)")
        
        if dfs:
            result = pd.concat(dfs, ignore_index=True)
            print(f"\nTotal loaded records: {len(result)}")
            return result
        else:
            return pd.DataFrame()


def periodic_collection(currency='BTC', interval_minutes=5, iterations=12):
    """
    Collect data every N minutes and save to Parquet
    
    Args:
        currency (str): currency ('BTC', 'ETH')
        interval_minutes (int): collection interval in minutes
        iterations (int): number of iterations
    """
    collector = DeribitDataCollector(currency=currency)
    
    for i in range(iterations):
        print(f"\n{'='*50}")
        print(f"Iteration {i+1}/{iterations} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*50}")
        
        df = collector.collect_options_data()
        collector.save_to_parquet(df)
        
        if i < iterations - 1:
            print(f"\nWaiting {interval_minutes} minutes...")
            time.sleep(interval_minutes * 60)


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # 1. Simple data collection for ETH options
    collector = DeribitDataCollector(currency='ETH', data_dir='deribit_data')
    df = collector.collect_options_data()
    
    # Save to Parquet
    collector.save_to_parquet(df)
    
    # 2. View data
    print("\nFirst rows:")
    print(df.head())
    
    print("\nData info:")
    print(df.info())
    
    # 3. Analyze collected data
    if not df.empty:
        print("\n=== Quick Statistics ===")
        print(f"Total options: {len(df)}")
        print(f"Calls: {len(df[df['option_type'] == 'call'])}")
        print(f"Puts: {len(df[df['option_type'] == 'put'])}")
        print(f"\nUnique expirations: {df['expiration_timestamp'].nunique()}")
        print(f"Unique strikes: {df['strike'].nunique()}")
        
        # Filter data - for example, only liquid options
        df_liquid = df[
            (df['bid_price'].notna()) & 
            (df['ask_price'].notna()) &
            (df['open_interest'] > 0)
        ]
        print(f"\nLiquid options (with non-zero OI and spread): {len(df_liquid)}")
    
    # 4. To run periodic collection uncomment:
    # periodic_collection(currency='ETH', interval_minutes=2, iterations=10)
