"""CryptoPanic news provider for market sentiment.

Fetches crypto news and sentiment data from CryptoPanic API.
Used by the engine to gauge market sentiment and filter trades.

API Documentation: https://cryptopanic.com/developers/api/
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any

import httpx


class NewsSentiment(Enum):
    """Sentiment classification for news articles."""
    VERY_BEARISH = "very_bearish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    BULLISH = "bullish"
    VERY_BULLISH = "very_bullish"


class NewsKind(Enum):
    """Type of news content."""
    NEWS = "news"
    MEDIA = "media"


@dataclass
class NewsArticle:
    """Represents a single news article from CryptoPanic."""
    id: str
    title: str
    url: str
    source: str
    published_at: datetime
    currencies: list[str]
    kind: NewsKind
    sentiment: NewsSentiment | None = None
    votes_positive: int = 0
    votes_negative: int = 0
    votes_important: int = 0
    
    @property
    def sentiment_score(self) -> float:
        """Calculate sentiment score from -1 (bearish) to +1 (bullish)."""
        if self.sentiment == NewsSentiment.VERY_BULLISH:
            return 1.0
        elif self.sentiment == NewsSentiment.BULLISH:
            return 0.5
        elif self.sentiment == NewsSentiment.NEUTRAL:
            return 0.0
        elif self.sentiment == NewsSentiment.BEARISH:
            return -0.5
        elif self.sentiment == NewsSentiment.VERY_BEARISH:
            return -1.0
        
        # Calculate from votes if no sentiment
        total = self.votes_positive + self.votes_negative
        if total == 0:
            return 0.0
        return (self.votes_positive - self.votes_negative) / total
    
    @property
    def is_important(self) -> bool:
        """Check if article is marked as important."""
        return self.votes_important >= 3


@dataclass
class SentimentSummary:
    """Aggregate sentiment for a currency."""
    currency: str
    article_count: int
    avg_sentiment: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    important_articles: int
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def is_bullish(self) -> bool:
        """Check if overall sentiment is bullish."""
        return self.avg_sentiment > 0.2
    
    @property
    def is_bearish(self) -> bool:
        """Check if overall sentiment is bearish."""
        return self.avg_sentiment < -0.2
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "currency": self.currency,
            "article_count": self.article_count,
            "avg_sentiment": round(self.avg_sentiment, 3),
            "bullish_count": self.bullish_count,
            "bearish_count": self.bearish_count,
            "neutral_count": self.neutral_count,
            "important_articles": self.important_articles,
            "is_bullish": self.is_bullish,
            "is_bearish": self.is_bearish,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class CryptoPanicConfig:
    """CryptoPanic API configuration."""
    api_key: str
    enabled: bool = True
    # Filtering
    currencies: list[str] = field(default_factory=lambda: ["BTC", "ETH"])
    filter_kind: NewsKind | None = None  # None = all kinds
    # Caching
    cache_ttl_seconds: int = 300  # 5 minutes
    # Rate limiting
    requests_per_minute: int = 10


class CryptoPanicProvider:
    """CryptoPanic news and sentiment provider.
    
    Fetches crypto news from CryptoPanic API and calculates
    aggregate sentiment for trading decisions.
    
    Example:
        >>> config = CryptoPanicConfig(api_key="xxx")
        >>> async with CryptoPanicProvider(config) as provider:
        ...     sentiment = await provider.get_sentiment("BTC")
        ...     if sentiment.is_bearish:
        ...         print("Market sentiment negative, reduce position")
    """
    
    BASE_URL = "https://cryptopanic.com/api/v1"
    
    def __init__(self, config: CryptoPanicConfig):
        """Initialize provider.
        
        Args:
            config: API configuration
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None
        self._cache: dict[str, tuple[datetime, list[NewsArticle]]] = {}
        self._request_timestamps: list[datetime] = []
    
    async def __aenter__(self) -> "CryptoPanicProvider":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_news(
        self,
        currencies: list[str] | None = None,
        limit: int = 50,
        use_cache: bool = True,
    ) -> list[NewsArticle]:
        """Fetch news articles.
        
        Args:
            currencies: Currency symbols to filter (e.g., ["BTC", "ETH"])
            limit: Maximum articles to return
            use_cache: Whether to use cached results
            
        Returns:
            List of news articles
        """
        if not self.config.enabled or not self.config.api_key:
            return []
        
        currencies = currencies or self.config.currencies
        cache_key = ",".join(sorted(currencies))
        
        # Check cache
        if use_cache and cache_key in self._cache:
            cached_time, cached_articles = self._cache[cache_key]
            if datetime.now(timezone.utc) - cached_time < timedelta(seconds=self.config.cache_ttl_seconds):
                return cached_articles[:limit]
        
        # Rate limiting
        if not self._check_rate_limit():
            # Return cached if available, even if stale
            if cache_key in self._cache:
                return self._cache[cache_key][1][:limit]
            return []
        
        # Fetch from API
        articles = await self._fetch_news(currencies)
        
        # Update cache
        self._cache[cache_key] = (datetime.now(timezone.utc), articles)
        self._request_timestamps.append(datetime.now(timezone.utc))
        
        return articles[:limit]
    
    async def get_sentiment(
        self,
        currency: str,
        time_window_hours: int = 24,
    ) -> SentimentSummary:
        """Get aggregate sentiment for a currency.
        
        Args:
            currency: Currency symbol (e.g., "BTC")
            time_window_hours: How far back to look
            
        Returns:
            Sentiment summary
        """
        articles = await self.get_news(currencies=[currency])
        
        # Filter by time window
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
        recent = [a for a in articles if a.published_at >= cutoff]
        
        if not recent:
            return SentimentSummary(
                currency=currency,
                article_count=0,
                avg_sentiment=0.0,
                bullish_count=0,
                bearish_count=0,
                neutral_count=0,
                important_articles=0,
            )
        
        # Calculate aggregates
        sentiments = [a.sentiment_score for a in recent]
        avg_sentiment = sum(sentiments) / len(sentiments)
        
        bullish = sum(1 for s in sentiments if s > 0.2)
        bearish = sum(1 for s in sentiments if s < -0.2)
        neutral = len(sentiments) - bullish - bearish
        important = sum(1 for a in recent if a.is_important)
        
        return SentimentSummary(
            currency=currency,
            article_count=len(recent),
            avg_sentiment=avg_sentiment,
            bullish_count=bullish,
            bearish_count=bearish,
            neutral_count=neutral,
            important_articles=important,
        )
    
    async def get_multi_sentiment(
        self,
        currencies: list[str],
        time_window_hours: int = 24,
    ) -> dict[str, SentimentSummary]:
        """Get sentiment for multiple currencies.
        
        Args:
            currencies: List of currency symbols
            time_window_hours: How far back to look
            
        Returns:
            Dictionary of currency -> sentiment
        """
        results = {}
        for currency in currencies:
            results[currency] = await self.get_sentiment(currency, time_window_hours)
        return results
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now(timezone.utc)
        one_minute_ago = now - timedelta(minutes=1)
        
        # Clean old timestamps
        self._request_timestamps = [
            ts for ts in self._request_timestamps
            if ts >= one_minute_ago
        ]
        
        return len(self._request_timestamps) < self.config.requests_per_minute
    
    async def _fetch_news(self, currencies: list[str]) -> list[NewsArticle]:
        """Fetch news from CryptoPanic API."""
        if not self._client:
            async with httpx.AsyncClient(timeout=30.0) as client:
                return await self._do_fetch(client, currencies)
        return await self._do_fetch(self._client, currencies)
    
    async def _do_fetch(
        self,
        client: httpx.AsyncClient,
        currencies: list[str],
    ) -> list[NewsArticle]:
        """Execute API request."""
        params: dict[str, Any] = {
            "auth_token": self.config.api_key,
            "currencies": ",".join(currencies),
            "public": "true",
        }
        
        if self.config.filter_kind:
            params["kind"] = self.config.filter_kind.value
        
        try:
            response = await client.get(f"{self.BASE_URL}/posts/", params=params)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            return self._parse_articles(data.get("results", []))
        
        except (httpx.HTTPError, ValueError):
            return []
    
    def _parse_articles(self, results: list[dict[str, Any]]) -> list[NewsArticle]:
        """Parse API response into NewsArticle objects."""
        articles = []
        
        for item in results:
            try:
                # Parse sentiment if available
                sentiment = None
                votes = item.get("votes", {})
                
                # CryptoPanic provides vote counts, not direct sentiment
                positive = votes.get("positive", 0)
                negative = votes.get("negative", 0)
                
                if positive > negative * 2:
                    sentiment = NewsSentiment.BULLISH
                elif positive > negative:
                    sentiment = NewsSentiment.NEUTRAL
                elif negative > positive * 2:
                    sentiment = NewsSentiment.BEARISH
                elif negative > positive:
                    sentiment = NewsSentiment.NEUTRAL
                
                # Extract currencies
                currencies = [
                    c.get("code", "")
                    for c in item.get("currencies", [])
                ]
                
                article = NewsArticle(
                    id=str(item.get("id", "")),
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source=item.get("source", {}).get("title", "Unknown"),
                    published_at=datetime.fromisoformat(
                        item.get("published_at", "").replace("Z", "+00:00")
                    ),
                    currencies=currencies,
                    kind=NewsKind(item.get("kind", "news")),
                    sentiment=sentiment,
                    votes_positive=positive,
                    votes_negative=negative,
                    votes_important=votes.get("important", 0),
                )
                articles.append(article)
            except (KeyError, ValueError):
                # Skip malformed articles
                continue
        
        return articles
