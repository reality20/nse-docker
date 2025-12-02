import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi, type Time, AreaSeries } from 'lightweight-charts';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import { Activity, Wifi, WifiOff, TrendingUp, Clock } from 'lucide-react';

// NSE WebSocket URL
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${protocol}//${window.location.host}/ws`;

interface PriceData {
  symbol: string;
  price: number;
  timestamp: string; // ISO or similar
  server_time: number;
}

const ChartComponent: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const { lastJsonMessage, readyState } = useWebSocket(WS_URL, {
    shouldReconnect: () => true,
    reconnectInterval: 3000,
  });

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];

  useEffect(() => {
    if (chartContainerRef.current && !chartRef.current) {
      const chart = createChart(chartContainerRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: '#1a1a1a' },
          textColor: '#d1d5db',
        },
        grid: {
          vertLines: { color: '#2b2b2b' },
          horzLines: { color: '#2b2b2b' },
        },
        width: chartContainerRef.current.clientWidth,
        height: 500,
        timeScale: {
          timeVisible: true,
          secondsVisible: true,
        },
      });

      const newSeries = chart.addSeries(AreaSeries, {
        topColor: 'rgba(33, 150, 243, 0.56)',
        bottomColor: 'rgba(33, 150, 243, 0.04)',
        lineColor: 'rgba(33, 150, 243, 1)',
        lineWidth: 2,
      });

      chartRef.current = chart;
      seriesRef.current = newSeries;

      const handleResize = () => {
        if (chartRef.current && chartContainerRef.current) {
          chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };

      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
        chartRef.current = null;
      };
    }
  }, []);

  useEffect(() => {
    if (lastJsonMessage && seriesRef.current) {
      const data = lastJsonMessage as PriceData;

      // Try to parse the timestamp provided by NSE, or fall back to server time/local time
      // NSE usually provides timestamp like "27-Jan-2025 15:30:00" or similar string, or ISO
      // Lightweight charts needs unix timestamp in seconds

      let timeValue: number;
      if (data.server_time) {
          timeValue = Math.floor(data.server_time);
      } else {
          timeValue = Math.floor(Date.now() / 1000);
      }

      // Check if this time already exists in the series to avoid "Time must be distinct" error?
      // Actually lightweight charts handles updates to the *last* bar, but new bars must be strictly increasing.
      // If we get multiple ticks per second, we might have issues if we use 1s resolution.
      // Ideally we check if timeValue > lastTimeValue.

      seriesRef.current.update({ time: timeValue as Time, value: data.price });

      setCurrentPrice(data.price);
      setLastUpdate(new Date());
    }
  }, [lastJsonMessage]);

  return (
    <div className="flex flex-col h-screen bg-neutral-900 text-gray-100 font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-neutral-800 border-b border-neutral-700 shadow-md">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 p-2 rounded-lg">
            <TrendingUp size={24} className="text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">ProTrader NSE</h1>
            <p className="text-xs text-gray-400">NIFTY 50 Live Tick Data</p>
          </div>
        </div>

        <div className="flex items-center gap-6">
            <div className="flex flex-col items-end">
                <span className="text-2xl font-mono font-bold text-green-400">
                    {currentPrice ? currentPrice.toFixed(2) : 'Loading...'}
                </span>
                <span className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock size={10} />
                    {lastUpdate ? lastUpdate.toLocaleTimeString() : '--:--:--'}
                </span>
            </div>

            <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium ${readyState === ReadyState.OPEN ? 'bg-green-900/30 text-green-400 border border-green-800' : 'bg-red-900/30 text-red-400 border border-red-800'}`}>
                {readyState === ReadyState.OPEN ? <Wifi size={14} /> : <WifiOff size={14} />}
                {connectionStatus}
            </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 relative">
        <div className="w-full h-full bg-neutral-800 rounded-xl border border-neutral-700 shadow-inner overflow-hidden relative">
            <div ref={chartContainerRef} className="absolute inset-0" />

            {/* Overlay Watermark or Info */}
            <div className="absolute top-4 left-4 z-10 pointer-events-none">
                <h2 className="text-4xl font-black text-neutral-700 select-none">NIFTY 50</h2>
            </div>
        </div>
      </main>

        {/* Footer */}
        <footer className="px-6 py-2 bg-neutral-800 border-t border-neutral-700 text-xs text-gray-500 flex justify-between">
            <span>Data provided by NSE (Simulated Tick Stream via Official API Polling)</span>
            <span className="flex items-center gap-2">
                <Activity size={12} />
                Real-time connection
            </span>
        </footer>
    </div>
  );
};

export default ChartComponent;
