import pandas as pd
from lightweight_charts.widgets import StreamlitChart
print("Imports working. testing chart creation...")
chart = StreamlitChart(width=1000, height=500)
chart.layout(background_color='#131722', text_color='white')
df = pd.DataFrame({'time': ['2023-01-01', '2023-01-02'], 'open': [100, 101], 'high': [102, 103], 'low': [99, 100], 'close': [101, 102], 'volume': [1000, 1200]})
df['time'] = pd.to_datetime(df['time'])
chart.set(df)
print("Set df success")
