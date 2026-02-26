import { useEffect, useRef } from 'react';
import { useDashboardStore } from '@/lib/store';
import { auth } from '@/lib/firebase';
import { DASHBOARD_CONFIG } from "@/lib/config";
import { MOCK_BOT_STATE, MOCK_TRADES } from "@/lib/mock-data";

export function useDashboardWs() {
  const { setBotState, addTrade, addEvent, setConnected, updateHeartbeat } = useDashboardStore();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    let isMounted = true;

    // In mock mode, seed the store with demo data instead of connecting to WS
    if (DASHBOARD_CONFIG.USE_MOCK_DATA) {
      if (isMounted) {
        setBotState(MOCK_BOT_STATE);
        MOCK_TRADES.forEach((trade) => addTrade(trade));
        setConnected(true);
        updateHeartbeat();
      }
      return;
    }

    const connect = async () => {
      try {
        const user = auth.currentUser;
        let token = "";
        if (user) {
          try {
            token = await user.getIdToken();
          } catch (e) {
            console.warn("Failed to get ID token", e);
          }
        }

        const wsUrl = `${DASHBOARD_CONFIG.WS_URL}?token=${token}`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) setConnected(true);
        };

        ws.onclose = () => {
          if (isMounted) {
            setConnected(false);
            // Reconnect after 3s
            reconnectTimeoutRef.current = setTimeout(connect, 3000);
          }
        };

        ws.onerror = () => {
          // Standard WS error event doesn't give much info, but we know it closed
          // Browser console will show the connection refused error, which is unavoidable
          // when the server is down.
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === "status") {
              updateHeartbeat();
              if (data.payload?.status) {
                setBotState({ status: data.payload.status });
              }
            } else if (data.type === "trade") {
              addTrade(data.payload);
            } else if (data.type === "event") {
              addEvent({
                seq: data.cursor,
                type: data.event_type,
                level: data.level,
                payload: data.payload,
                timestamp: data.ts
              });
            } else if (data.type === "snapshot") {
              if (data.payload.equity_usd) {
                setBotState({ equity_usd: data.payload.equity_usd });
              }
            }

          } catch (e) {
            console.error("WS parse error", e);
          }
        };
      } catch (e) {
        console.error("WS connect error", e);
      }
    };

    connect();

    return () => {
      isMounted = false;
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [setBotState, addTrade, addEvent, setConnected, updateHeartbeat]);
}
