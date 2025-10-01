import numpy as np
from scipy.stats import norm

class OptionPricer:
    """
    Black-Scholes Pricing mit variabler (strike/maturity-abhängiger) Volatilität
    """
    
    def __init__(self, vol_surface):
        self.vol_surface = vol_surface
    
    def black_scholes_price(self, spot, strike, time_to_maturity, rate, 
                           option_type='call', dividend=0.0):
        """
        Black-Scholes mit Vol aus Surface
        """
        if time_to_maturity <= 0:
            return max(0, (spot - strike) if option_type == 'call' else (strike - spot))
        
        # Hole implied vol aus Surface
        sigma = self.vol_surface.implied_volatility(strike, spot, time_to_maturity, rate)
        
        # Black-Scholes Formula
        d1 = (np.log(spot / strike) + (rate - dividend + 0.5 * sigma**2) * time_to_maturity) / (sigma * np.sqrt(time_to_maturity))
        d2 = d1 - sigma * np.sqrt(time_to_maturity)
        
        if option_type == 'call':
            price = spot * np.exp(-dividend * time_to_maturity) * norm.cdf(d1) - \
                    strike * np.exp(-rate * time_to_maturity) * norm.cdf(d2)
        else:  # put
            price = strike * np.exp(-rate * time_to_maturity) * norm.cdf(-d2) - \
                    spot * np.exp(-dividend * time_to_maturity) * norm.cdf(-d1)
        
        return float(price)
    
    def calculate_greeks(self, spot, strike, time_to_maturity, rate, 
                        option_type='call', dividend=0.0):
        """
        Berechnet Delta, Gamma, Vega, Theta, Rho
        """
        if time_to_maturity <= 0:
            return {
                'delta': 1.0 if option_type == 'call' else -1.0,
                'gamma': 0.0,
                'vega': 0.0,
                'theta': 0.0,
                'rho': 0.0
            }
        
        sigma = self.vol_surface.implied_volatility(strike, spot, time_to_maturity, rate)
        sqrt_T = np.sqrt(time_to_maturity)
        
        d1 = (np.log(spot / strike) + (rate - dividend + 0.5 * sigma**2) * time_to_maturity) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T
        
        # Greeks
        if option_type == 'call':
            delta = np.exp(-dividend * time_to_maturity) * norm.cdf(d1)
            theta = (-spot * norm.pdf(d1) * sigma * np.exp(-dividend * time_to_maturity) / (2 * sqrt_T) - 
                    rate * strike * np.exp(-rate * time_to_maturity) * norm.cdf(d2) + 
                    dividend * spot * np.exp(-dividend * time_to_maturity) * norm.cdf(d1))
            rho = strike * time_to_maturity * np.exp(-rate * time_to_maturity) * norm.cdf(d2) / 100
        else:  # put
            delta = -np.exp(-dividend * time_to_maturity) * norm.cdf(-d1)
            theta = (-spot * norm.pdf(d1) * sigma * np.exp(-dividend * time_to_maturity) / (2 * sqrt_T) + 
                    rate * strike * np.exp(-rate * time_to_maturity) * norm.cdf(-d2) - 
                    dividend * spot * np.exp(-dividend * time_to_maturity) * norm.cdf(-d1))
            rho = -strike * time_to_maturity * np.exp(-rate * time_to_maturity) * norm.cdf(-d2) / 100
        
        gamma = norm.pdf(d1) * np.exp(-dividend * time_to_maturity) / (spot * sigma * sqrt_T)
        vega = spot * norm.pdf(d1) * sqrt_T * np.exp(-dividend * time_to_maturity) / 100
        
        return {
            'delta': float(delta),
            'gamma': float(gamma),
            'vega': float(vega),
            'theta': float(theta / 365),  # per day
            'rho': float(rho)
        }
