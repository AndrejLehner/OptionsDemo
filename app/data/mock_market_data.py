import numpy as np

class MockMarketData:
    """
    Generiert realistische Mock-Daten für Options-Trading
    """
    
    @staticmethod
    def get_underlyings():
        return [
            {
                'symbol': 'DAX',
                'name': 'DAX Index',
                'spot': 15500.0,
                'currency': 'EUR'
            },
            {
                'symbol': 'AAPL',
                'name': 'Apple Inc.',
                'spot': 175.0,
                'currency': 'USD'
            },
            {
                'symbol': 'TSLA',
                'name': 'Tesla Inc.',
                'spot': 250.0,
                'currency': 'USD'
            }
        ]
    
    @staticmethod
    def get_risk_free_rate():
        return 0.045  # 4.5% (realistisch für 2025)
    
    @staticmethod
    def generate_option_chain(underlying_symbol, spot_price):
        """
        Generiert Option-Chain für gegebenes Underlying
        """
        strikes = np.linspace(spot_price * 0.8, spot_price * 1.2, 9)
        maturities = [0.25, 0.5, 1.0]  # 3M, 6M, 1Y
        maturity_labels = ['3M', '6M', '1Y']
        
        options = []
        for i, T in enumerate(maturities):
            for K in strikes:
                moneyness = K / spot_price
                options.append({
                    'id': f'{underlying_symbol}-{int(K)}-{maturity_labels[i]}',
                    'underlying': underlying_symbol,
                    'strike': float(K),
                    'maturity': float(T),
                    'maturity_label': maturity_labels[i],
                    'moneyness': float(moneyness),
                    'type': 'call'
                })
        
        return options