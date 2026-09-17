"""
Generated Pocket Option client
DO NOT EDIT - This file is auto-generated
Generated on: 2026-04-06 22:23:07
Version: 2.0.0
"""

import typing
from typing import Optional, Callable, Awaitable, Any

from pocket_trader import models
from pocket_trader.client import BasePocketOptionClient

from pocket_trader.types import TypedEventListener
from typing import Any

if typing.TYPE_CHECKING:
    from pocket_trader.types import TypedEventListener

__all__ = ("PocketOptionClient",)


class PocketOptionClientEmit:
    """
    Emit methods for Pocket Option client

    This class contains all methods for sending events to the server.
    Each method corresponds to a specific event type.
    """

    def __init__(self, client: BasePocketOptionClient) -> None:
        self.client = client

    async def ps(self) -> None:
        """
        Send ping to server

        """
        await self.client.send("ps")

    async def indicator_load(self) -> None:
        """
        Load indicators

        """
        await self.client.send("indicator/load")

    async def favorite_load(self) -> None:
        """
        Load favorites

        """
        await self.client.send("favorite/load")

    async def price_alert_load(self) -> None:
        """
        Load price alerts

        """
        await self.client.send("price-alert/load")

    async def auth(self, data: models.AuthorizationData) -> None:
        """
        Authenticate with server

        Args:
            data: models.AuthorizationData - Event data
        """
        await self.client.send("auth", data)

    async def subscribe_to_asset(self, asset: models.Asset) -> None:
        """
        Subscribe to asset for real-time updates

        Args:
            asset: models.Asset - Event data
        """
        await self.client.send("subscribeSymbol", asset)

    async def unsubscribe_from_asset(self, asset: models.Asset) -> None:
        """
        Unsubscribe from asset updates

        Args:
            asset: models.Asset - Event data
        """
        await self.client.send("unsubscribeSymbol", asset)

    async def subscribe_for_market_sentiment(self, asset: models.Asset) -> None:
        """
        Subscribe to market sentiment for asset

        Args:
            asset: models.Asset - Event data
        """
        await self.client.send("subfor", asset)

    async def unsubscribe_for_market_sentiment(self, asset: models.Asset) -> None:
        """
        Unsubscribe from market sentiment

        Args:
            asset: models.Asset - Event data
        """
        await self.client.send("unsubfor", asset)

    async def change_asset(self, data: models.ChangeAssetRequest) -> None:
        """
        Change current asset

        Args:
            data: models.ChangeAssetRequest - Event data
        """
        await self.client.send("changeSymbol", data)

    async def open_deal(self, data: models.OpenDealRequest) -> None:
        """
        Open a new deal/trade

        Args:
            data: models.OpenDealRequest - Event data
        """
        await self.client.send("openOrder", data)

    async def close_deal(self, deal_id: str) -> None:
        """
        Close an existing deal

        Args:
            deal_id: str - Event data
        """
        await self.client.send("closeOrder", deal_id)

    async def cancel_pending_deal(self, deal_id: str) -> None:
        """
        Cancel a pending deal

        Args:
            deal_id: str - Event data
        """
        await self.client.send("cancelPendingOrder", deal_id)

    async def copy_signal(self, data: models.CopySignalRequest) -> None:
        """
        Copy a signal from another trader

        Args:
            data: models.CopySignalRequest - Event data
        """
        await self.client.send("copySignalOrder", data)

    async def get_candles(self, data: dict) -> None:
        """
        Request historical candles

        Args:
            data: dict - Event data
        """
        await self.client.send("getCandles", data)

    async def get_history(self, data: dict) -> None:
        """
        Request trading history

        Args:
            data: dict - Event data
        """
        await self.client.send("getHistory", data)

    async def get_assets(self) -> None:
        """
        Request available assets

        """
        await self.client.send("getAssets")

    async def get_balance(self) -> None:
        """
        Request current balance

        """
        await self.client.send("getBalance")


class PocketOptionClientOn:
    """
    Event handlers for Pocket Option client

    This class contains all methods for handling incoming events.
    Each method can be used as a decorator or called directly.

    Example:
        @client.on.update_balance
        async def handle_balance(data: models.SuccessUpdateBalanceEvent):
            print(f"New balance: {data.balance}")
    """

    def __init__(self, client: BasePocketOptionClient) -> None:
        self.client = client

    @typing.overload
    def update_balance(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[models.SuccessUpdateBalanceEvent]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_balance(self, handler: TypedEventListener[models.SuccessUpdateBalanceEvent]) -> None:
        """Direct call overload"""
        ...

    def update_balance(
        self, handler: Optional[TypedEventListener[models.SuccessUpdateBalanceEvent]] = None
    ) -> Optional[Callable[[TypedEventListener[models.SuccessUpdateBalanceEvent]], None]]:
        """
        Handle balance update events

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_balance
            async def handler(data: models.SuccessUpdateBalanceEvent):
                print(data)
        """
        return self.client.add_on(
            "successupdateBalance", handler=handler, model=models.SuccessUpdateBalanceEvent
        )

    @typing.overload
    def update_history_new_fast(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[models.UpdateHistoryFastEvent]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_history_new_fast(
        self, handler: TypedEventListener[models.UpdateHistoryFastEvent]
    ) -> None:
        """Direct call overload"""
        ...

    def update_history_new_fast(
        self, handler: Optional[TypedEventListener[models.UpdateHistoryFastEvent]] = None
    ) -> Optional[Callable[[TypedEventListener[models.UpdateHistoryFastEvent]], None]]:
        """
        Handle historical candle updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_history_new_fast
            async def handler(data: models.UpdateHistoryFastEvent):
                print(data)
        """
        return self.client.add_on(
            "updateHistoryNewFast", handler=handler, model=models.UpdateHistoryFastEvent
        )

    @typing.overload
    def update_close_value(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_close_value(self, handler: TypedEventListener[list]) -> None:
        """Direct call overload"""
        ...

    def update_close_value(
        self, handler: Optional[TypedEventListener[list]] = None
    ) -> Optional[Callable[[TypedEventListener[list]], None]]:
        """
        Handle real-time price updates (39-byte stream)

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_close_value
            async def handler(data: list):
                print(data)
        """
        return self.client.add_on("updateStream", handler=handler, model=None)

    @typing.overload
    def update_opened_deals(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list[models.Deal]]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_opened_deals(self, handler: TypedEventListener[list[models.Deal]]) -> None:
        """Direct call overload"""
        ...

    def update_opened_deals(
        self, handler: Optional[TypedEventListener[list[models.Deal]]] = None
    ) -> Optional[Callable[[TypedEventListener[list[models.Deal]]], None]]:
        """
        Handle opened deals updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_opened_deals
            async def handler(data: list[models.Deal]):
                print(data)
        """
        return self.client.add_on(
            "updateOpenedDeals", handler=handler, model=models.DealListTypeAdapter
        )

    @typing.overload
    def success_open_deal(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[models.Deal]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def success_open_deal(self, handler: TypedEventListener[models.Deal]) -> None:
        """Direct call overload"""
        ...

    def success_open_deal(
        self, handler: Optional[TypedEventListener[models.Deal]] = None
    ) -> Optional[Callable[[TypedEventListener[models.Deal]], None]]:
        """
        Handle successful deal opening

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.success_open_deal
            async def handler(data: models.Deal):
                print(data)
        """
        return self.client.add_on("successopenOrder", handler=handler, model=models.Deal)

    @typing.overload
    def update_closed_deals(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list[models.Deal]]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_closed_deals(self, handler: TypedEventListener[list[models.Deal]]) -> None:
        """Direct call overload"""
        ...

    def update_closed_deals(
        self, handler: Optional[TypedEventListener[list[models.Deal]]] = None
    ) -> Optional[Callable[[TypedEventListener[list[models.Deal]]], None]]:
        """
        Handle closed deals updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_closed_deals
            async def handler(data: list[models.Deal]):
                print(data)
        """
        return self.client.add_on(
            "updateClosedDeals", handler=handler, model=models.DealListTypeAdapter
        )

    @typing.overload
    def update_assets(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list[models.UpdateAssetItem]]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_assets(self, handler: TypedEventListener[list[models.UpdateAssetItem]]) -> None:
        """Direct call overload"""
        ...

    def update_assets(
        self, handler: Optional[TypedEventListener[list[models.UpdateAssetItem]]] = None
    ) -> Optional[Callable[[TypedEventListener[list[models.UpdateAssetItem]]], None]]:
        """
        Handle asset updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_assets
            async def handler(data: list[models.UpdateAssetItem]):
                print(data)
        """
        return self.client.add_on(
            "updateAssets", handler=handler, model=models.UpdateAssetItemListTypeAdapter
        )

    @typing.overload
    def success_close_deal(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[models.SuccessCloseDealEvent]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def success_close_deal(self, handler: TypedEventListener[models.SuccessCloseDealEvent]) -> None:
        """Direct call overload"""
        ...

    def success_close_deal(
        self, handler: Optional[TypedEventListener[models.SuccessCloseDealEvent]] = None
    ) -> Optional[Callable[[TypedEventListener[models.SuccessCloseDealEvent]], None]]:
        """
        Handle successful deal closing

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.success_close_deal
            async def handler(data: models.SuccessCloseDealEvent):
                print(data)
        """
        return self.client.add_on(
            "successcloseOrder", handler=handler, model=models.SuccessCloseDealEvent
        )

    @typing.overload
    def success_update_pending(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def success_update_pending(self, handler: TypedEventListener[list]) -> None:
        """Direct call overload"""
        ...

    def success_update_pending(
        self, handler: Optional[TypedEventListener[list]] = None
    ) -> Optional[Callable[[TypedEventListener[list]], None]]:
        """
        Handle pending deals updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.success_update_pending
            async def handler(data: list):
                print(data)
        """
        return self.client.add_on("successupdatePending", handler=handler, model=None)

    @typing.overload
    def update_charts(self, handler: None = None) -> Callable[[TypedEventListener[list]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_charts(self, handler: TypedEventListener[list]) -> None:
        """Direct call overload"""
        ...

    def update_charts(
        self, handler: Optional[TypedEventListener[list]] = None
    ) -> Optional[Callable[[TypedEventListener[list]], None]]:
        """
        Handle chart updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_charts
            async def handler(data: list):
                print(data)
        """
        return self.client.add_on("updateCharts", handler=handler, model=None)

    @typing.overload
    def update_indicators(self, handler: None = None) -> Callable[[TypedEventListener[dict]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_indicators(self, handler: TypedEventListener[dict]) -> None:
        """Direct call overload"""
        ...

    def update_indicators(
        self, handler: Optional[TypedEventListener[dict]] = None
    ) -> Optional[Callable[[TypedEventListener[dict]], None]]:
        """
        Handle indicators updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_indicators
            async def handler(data: dict):
                print(data)
        """
        return self.client.add_on("updateIndicators", handler=handler, model=None)

    @typing.overload
    def update_favorites(self, handler: None = None) -> Callable[[TypedEventListener[list]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_favorites(self, handler: TypedEventListener[list]) -> None:
        """Direct call overload"""
        ...

    def update_favorites(
        self, handler: Optional[TypedEventListener[list]] = None
    ) -> Optional[Callable[[TypedEventListener[list]], None]]:
        """
        Handle favorites updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_favorites
            async def handler(data: list):
                print(data)
        """
        return self.client.add_on("updateFavorites", handler=handler, model=None)

    @typing.overload
    def update_price_alerts(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def update_price_alerts(self, handler: TypedEventListener[list]) -> None:
        """Direct call overload"""
        ...

    def update_price_alerts(
        self, handler: Optional[TypedEventListener[list]] = None
    ) -> Optional[Callable[[TypedEventListener[list]], None]]:
        """
        Handle price alerts updates

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.update_price_alerts
            async def handler(data: list):
                print(data)
        """
        return self.client.add_on("updatePriceAlerts", handler=handler, model=None)

    @typing.overload
    def success_auth(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[models.SuccessAuthEvent]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def success_auth(self, handler: TypedEventListener[models.SuccessAuthEvent]) -> None:
        """Direct call overload"""
        ...

    def success_auth(
        self, handler: Optional[TypedEventListener[models.SuccessAuthEvent]] = None
    ) -> Optional[Callable[[TypedEventListener[models.SuccessAuthEvent]], None]]:
        """
        Handle successful authentication

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.success_auth
            async def handler(data: models.SuccessAuthEvent):
                print(data)
        """
        return self.client.add_on("successauth", handler=handler, model=models.SuccessAuthEvent)

    @typing.overload
    def change_market_sentiment(
        self, handler: None = None
    ) -> Callable[[TypedEventListener[list[models.MarketSentimentItem]]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def change_market_sentiment(
        self, handler: TypedEventListener[list[models.MarketSentimentItem]]
    ) -> None:
        """Direct call overload"""
        ...

    def change_market_sentiment(
        self, handler: Optional[TypedEventListener[list[models.MarketSentimentItem]]] = None
    ) -> Optional[Callable[[TypedEventListener[list[models.MarketSentimentItem]]], None]]:
        """
        Handle market sentiment changes (19-byte signals)

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.change_market_sentiment
            async def handler(data: list[models.MarketSentimentItem]):
                print(data)
        """
        return self.client.add_on(
            "chafor", handler=handler, model=models.MarketSentimentItemListTypeAdapter
        )

    @typing.overload
    def ping_server(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def ping_server(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def ping_server(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle server ping

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.ping_server
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("ping-server", handler=handler, model=None)

    @typing.overload
    def pong(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def pong(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def pong(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle server pong response

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.pong
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("pong", handler=handler, model=None)

    @typing.overload
    def connect(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def connect(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def connect(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle connection event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.connect
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("connect", handler=handler, model=None)

    @typing.overload
    def disconnect(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def disconnect(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def disconnect(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle disconnection event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.disconnect
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("disconnect", handler=handler, model=None)

    @typing.overload
    def reconnect(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def reconnect(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def reconnect(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle reconnect event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.reconnect
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("reconnect", handler=handler, model=None)

    @typing.overload
    def reconnect_attempt(self, handler: None = None) -> Callable[[TypedEventListener[int]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def reconnect_attempt(self, handler: TypedEventListener[int]) -> None:
        """Direct call overload"""
        ...

    def reconnect_attempt(
        self, handler: Optional[TypedEventListener[int]] = None
    ) -> Optional[Callable[[TypedEventListener[int]], None]]:
        """
        Handle reconnect attempt event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.reconnect_attempt
            async def handler(data: int):
                print(data)
        """
        return self.client.add_on("reconnect_attempt", handler=handler, model=None)

    @typing.overload
    def reconnecting(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def reconnecting(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def reconnecting(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle reconnecting event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.reconnecting
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("reconnecting", handler=handler, model=None)

    @typing.overload
    def reconnect_error(self, handler: None = None) -> Callable[[TypedEventListener[Any]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def reconnect_error(self, handler: TypedEventListener[Any]) -> None:
        """Direct call overload"""
        ...

    def reconnect_error(
        self, handler: Optional[TypedEventListener[Any]] = None
    ) -> Optional[Callable[[TypedEventListener[Any]], None]]:
        """
        Handle reconnect error event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.reconnect_error
            async def handler(data: Any):
                print(data)
        """
        return self.client.add_on("reconnect_error", handler=handler, model=None)

    @typing.overload
    def reconnect_failed(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def reconnect_failed(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def reconnect_failed(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle reconnect failed event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.reconnect_failed
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("reconnect_failed", handler=handler, model=None)

    @typing.overload
    def error(self, handler: None = None) -> Callable[[TypedEventListener[Any]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def error(self, handler: TypedEventListener[Any]) -> None:
        """Direct call overload"""
        ...

    def error(
        self, handler: Optional[TypedEventListener[Any]] = None
    ) -> Optional[Callable[[TypedEventListener[Any]], None]]:
        """
        Handle socket.io error events

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.error
            async def handler(data: Any):
                print(data)
        """
        return self.client.add_on("error", handler=handler, model=None)

    @typing.overload
    def connect_error(self, handler: None = None) -> Callable[[TypedEventListener[Any]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def connect_error(self, handler: TypedEventListener[Any]) -> None:
        """Direct call overload"""
        ...

    def connect_error(
        self, handler: Optional[TypedEventListener[Any]] = None
    ) -> Optional[Callable[[TypedEventListener[Any]], None]]:
        """
        Handle connection error event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.connect_error
            async def handler(data: Any):
                print(data)
        """
        return self.client.add_on("connect_error", handler=handler, model=None)

    @typing.overload
    def connecting(self, handler: None = None) -> Callable[[TypedEventListener[None]], None]:
        """Decorator overload"""
        ...

    @typing.overload
    def connecting(self, handler: TypedEventListener[None]) -> None:
        """Direct call overload"""
        ...

    def connecting(
        self, handler: Optional[TypedEventListener[None]] = None
    ) -> Optional[Callable[[TypedEventListener[None]], None]]:
        """
        Handle connecting event

        Args:
            handler: Async or sync callback function

        Returns:
            Decorator function if handler is None, otherwise None

        Example:
            @client.on.connecting
            async def handler(data: None):
                print(data)
        """
        return self.client.add_on("connecting", handler=handler, model=None)


class PocketOptionClient(BasePocketOptionClient):
    """
    Complete Pocket Option client

    This is the main client class that combines all functionality.
    Use `on` for event handlers and `emit` for sending events.

    Example:
        client = PocketOptionClient()
        await client.connect("wss://api-eu.po.market")
        await client.emit.auth(auth_data)

        @client.on.update_balance
        async def on_balance(data):
            print(f"Balance: {data.balance}")
    """

    @property
    def on(self) -> PocketOptionClientOn:
        """Get event handlers namespace"""
        return PocketOptionClientOn(self)

    @property
    def emit(self) -> PocketOptionClientEmit:
        """Get emit methods namespace"""
        return PocketOptionClientEmit(self)
