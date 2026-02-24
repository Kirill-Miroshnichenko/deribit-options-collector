"""
Basic Usage Example

Demonstrates simple usage of the Deribit options data collector
"""

import sys
sys.path.append('..')

from collector import DeribitDataCollector
import pandas as pd

def main():
    print("="*60)
    print("Deribit Options Collector - Basic Example")
    print("="*60)
    
    # Initialize collector
    collector = DeribitDataCollector(
        currency='ETH',
        data_dir='../deribit_data'
    )
    
    # Collect data
    print("\nCollecting current market data...")
    df = collector.collect_options_data()
    
    if not df.empty:
        # Save
        filepath = collector.save_to_parquet(df)
        
        # Display statistics
        print(f"\n{'='*60}")
        print("COLLECTION STATISTICS")
        print(f"{'='*60}")
        print(f"Total records:         {len(df)}")
        print(f"Unique instruments:    {df['instrument_name'].nunique()}")
        print(f"Data completeness:     {(1 - df.isnull().sum().sum() / df.size) * 100:.1f}%")
        
        # Top 10 by volume
        print(f"\nTop 10 options by 24h volume:")
        top_volume = df.nlargest(10, 'volume_24h')[
            ['instrument_name', 'mark_price', 'delta', 'mark_iv', 'volume_24h']
        ]
        print(top_volume.to_string(index=False))
        
        # ATM options
        print(f"\nATM (At-The-Money) options:")
        underlying = df['underlying_price'].iloc[0]
        atm_options = df[
            (df['strike'] >= underlying * 0.95) & 
            (df['strike'] <= underlying * 1.05)
        ].sort_values('strike')[
            ['instrument_name', 'strike', 'mark_price', 'delta', 'mark_iv']
        ]
        print(atm_options.head(10).to_string(index=False))
        
        # Liquidity analysis
        df_liquid = df[
            (df['bid_price'].notna()) & 
            (df['ask_price'].notna()) &
            (df['open_interest'] > 0)
        ]
        print(f"\nLiquid options: {len(df_liquid)} ({len(df_liquid)/len(df)*100:.1f}%)")
        
        print(f"\n✓ Data saved: {filepath}")
        
    else:
        print("✗ Data collection failed")


if __name__ == "__main__":
    main()
