"""
Data Analysis Example

Shows how to analyze and visualize collected options data
"""

import sys
sys.path.append('..')

from collector import DeribitDataCollector
import pandas as pd
import matplotlib.pyplot as plt

def analyze_volatility_smile(df):
    """Build volatility smile"""
    
    # Convert expiration timestamp
    df['expiration_date'] = pd.to_datetime(df['expiration_timestamp'], unit='ms')
    
    # Take nearest expiration
    nearest_exp = df['expiration_date'].min()
    exp_data = df[df['expiration_date'] == nearest_exp].copy()
    
    if len(exp_data) == 0:
        print("No data for analysis")
        return
    
    # Get underlying price
    underlying = exp_data['underlying_price'].iloc[0]
    
    # Calculate moneyness
    exp_data['moneyness'] = exp_data['strike'] / underlying
    
    # Separate calls and puts
    calls = exp_data[exp_data['option_type'] == 'call']
    puts = exp_data[exp_data['option_type'] == 'put']
    
    # Plot
    plt.figure(figsize=(12, 6))
    
    plt.scatter(calls['moneyness'], calls['mark_iv'] * 100, 
               alpha=0.6, label='Calls', color='green', s=50)
    plt.scatter(puts['moneyness'], puts['mark_iv'] * 100, 
               alpha=0.6, label='Puts', color='red', s=50)
    
    plt.axvline(x=1.0, color='gray', linestyle='--', alpha=0.5, label='ATM')
    
    plt.xlabel('Moneyness (Strike / Spot)', fontsize=12)
    plt.ylabel('Implied Volatility (%)', fontsize=12)
    plt.title(f'Volatility Smile - {nearest_exp.date()}', fontsize=14, fontweight='bold')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('volatility_smile.png', dpi=300)
    print(f"✓ Plot saved: volatility_smile.png")
    plt.show()


def analyze_greeks_distribution(df):
    """Analyze Greeks distribution"""
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Delta
    axes[0, 0].hist(df['delta'].dropna(), bins=50, alpha=0.7, color='blue', edgecolor='black')
    axes[0, 0].set_xlabel('Delta')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Delta Distribution')
    axes[0, 0].grid(True, alpha=0.3)
    
    # Gamma
    axes[0, 1].hist(df['gamma'].dropna(), bins=50, alpha=0.7, color='green', edgecolor='black')
    axes[0, 1].set_xlabel('Gamma')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Gamma Distribution')
    axes[0, 1].grid(True, alpha=0.3)
    
    # Vega
    axes[1, 0].hist(df['vega'].dropna(), bins=50, alpha=0.7, color='orange', edgecolor='black')
    axes[1, 0].set_xlabel('Vega')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Vega Distribution')
    axes[1, 0].grid(True, alpha=0.3)
    
    # Theta
    axes[1, 1].hist(df['theta'].dropna(), bins=50, alpha=0.7, color='red', edgecolor='black')
    axes[1, 1].set_xlabel('Theta')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Theta Distribution')
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('greeks_distribution.png', dpi=300)
    print(f"✓ Plot saved: greeks_distribution.png")
    plt.show()


def print_summary_stats(df):
    """Print summary statistics"""
    
    print(f"\n{'='*60}")
    print("SUMMARY STATISTICS")
    print(f"{'='*60}")
    
    print(f"\nGeneral data:")
    print(f"  Total options:      {len(df)}")
    print(f"  Calls:              {len(df[df['option_type'] == 'call'])}")
    print(f"  Puts:               {len(df[df['option_type'] == 'put'])}")
    
    print(f"\nImplied Volatility:")
    print(f"  Mean:      {df['mark_iv'].mean()*100:.2f}%")
    print(f"  Median:    {df['mark_iv'].median()*100:.2f}%")
    print(f"  Min:       {df['mark_iv'].min()*100:.2f}%")
    print(f"  Max:       {df['mark_iv'].max()*100:.2f}%")
    
    print(f"\nOpen Interest:")
    print(f"  Total:     {df['open_interest'].sum():,.0f}")
    print(f"  Mean:      {df['open_interest'].mean():.2f}")
    
    print(f"\n24h Volume:")
    print(f"  Total:     {df['volume_24h'].sum():,.0f}")
    print(f"  Mean:      {df['volume_24h'].mean():.2f}")
    
    # Top strikes by OI
    print(f"\nTop 5 strikes by Open Interest:")
    top_oi = df.groupby('strike')['open_interest'].sum().nlargest(5)
    for strike, oi in top_oi.items():
        print(f"  ${strike:.0f}: {oi:,.0f}")


def main():
    print("="*60)
    print("Deribit Options Data Analysis")
    print("="*60)
    
    # Load data
    import glob
    files = glob.glob('../deribit_data/*.parquet')
    
    if not files:
        print("\nNo data to analyze!")
        print("Run basic_usage.py to collect data first")
        return
    
    # Take latest file
    latest_file = max(files, key=lambda x: x)
    print(f"\nLoading: {latest_file}")
    
    df = pd.read_parquet(latest_file)
    
    print(f"Records: {len(df):,}")
    print(f"Instruments: {df['instrument_name'].nunique()}")
    print(f"Timestamp: {df['timestamp'].iloc[0]}")
    
    # Analyses
    print(f"\n{'='*60}")
    print("1. Summary Statistics")
    print(f"{'='*60}")
    print_summary_stats(df)
    
    print(f"\n{'='*60}")
    print("2. Volatility Smile")
    print(f"{'='*60}")
    analyze_volatility_smile(df)
    
    print(f"\n{'='*60}")
    print("3. Greeks Distribution")
    print(f"{'='*60}")
    analyze_greeks_distribution(df)


if __name__ == "__main__":
    main()
