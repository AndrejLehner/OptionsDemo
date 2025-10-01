import numpy as np
from scipy.optimize import minimize

class SVIVolatilitySurface:
    """
    SVI (Stochastic Volatility Inspired) Model für Volatility Surface
    w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))
    """
    
    def __init__(self, params=None):
        # Default Parameter für realistische Vol-Surface
        if params is None:
            self.params = {
                'a': 0.04,      # Niveau
                'b': 0.4,       # Steigung
                'rho': -0.4,    # Skew (negativ = typischer Equity Smile)
                'm': 0.0,       # ATM Position
                'sigma': 0.2    # Konvexität
            }
        else:
            self.params = params
    
    def total_variance(self, log_moneyness):
        """
        Berechnet Total Variance w(k) für gegebenen log-moneyness
        k = log(K/F) wobei K=Strike, F=Forward
        """
        k = log_moneyness
        p = self.params
        
        return p['a'] + p['b'] * (
            p['rho'] * (k - p['m']) + 
            np.sqrt((k - p['m'])**2 + p['sigma']**2)
        )
    
    def implied_volatility(self, strike, spot, time_to_maturity, rate=0.0):
        """
        Berechnet implizite Volatilität für gegebene Parameter
        """
        forward = spot * np.exp(rate * time_to_maturity)
        log_moneyness = np.log(strike / forward)
        
        # Total variance
        w = self.total_variance(log_moneyness)
        
        # Implied vol: sigma = sqrt(w / T)
        if time_to_maturity > 0:
            return np.sqrt(w / time_to_maturity)
        return np.sqrt(w)
    
    def generate_surface(self, spot=100, strikes=None, maturities=None, rate=0.0):
        """
        Generiert komplette Volatility Surface
        """
        if strikes is None:
            strikes = np.linspace(spot * 0.7, spot * 1.3, 20)
        if maturities is None:
            maturities = np.array([0.25, 0.5, 1.0, 2.0])  # 3M, 6M, 1Y, 2Y
        
        surface = []
        for T in maturities:
            for K in strikes:
                vol = self.implied_volatility(K, spot, T, rate)
                surface.append({
                    'strike': float(K),
                    'maturity': float(T),
                    'moneyness': float(K/spot),
                    'implied_vol': float(vol)
                })
        
        return surface
