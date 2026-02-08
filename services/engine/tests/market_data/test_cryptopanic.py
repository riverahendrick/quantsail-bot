"""Tests for CryptoPanic news provider."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from quantsail_engine.market_data.cryptopanic import (
    CryptoPanicConfig,
    CryptoPanicProvider,
    NewsArticle,
    NewsKind,
    NewsSentiment,
    SentimentSummary,
)


class TestNewsArticle:
    """Test suite for NewsArticle."""

    def test_sentiment_score_very_bullish(self):
        """Test sentiment score for very bullish."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            sentiment=NewsSentiment.VERY_BULLISH,
        )
        assert article.sentiment_score == 1.0

    def test_sentiment_score_very_bearish(self):
        """Test sentiment score for very bearish."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            sentiment=NewsSentiment.VERY_BEARISH,
        )
        assert article.sentiment_score == -1.0

    def test_sentiment_score_from_votes(self):
        """Test sentiment score calculated from votes."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            sentiment=None,
            votes_positive=8,
            votes_negative=2,
        )
        assert article.sentiment_score == 0.6  # (8-2)/10

    def test_sentiment_score_no_votes(self):
        """Test sentiment score with no votes."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            sentiment=None,
        )
        assert article.sentiment_score == 0.0

    def test_is_important(self):
        """Test importance detection."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            votes_important=5,
        )
        assert article.is_important is True

    def test_not_important(self):
        """Test non-important article."""
        article = NewsArticle(
            id="1",
            title="Test",
            url="http://test.com",
            source="Test",
            published_at=datetime.now(timezone.utc),
            currencies=["BTC"],
            kind=NewsKind.NEWS,
            votes_important=2,
        )
        assert article.is_important is False


class TestSentimentSummary:
    """Test suite for SentimentSummary."""

    def test_is_bullish(self):
        """Test bullish detection."""
        summary = SentimentSummary(
            currency="BTC",
            article_count=10,
            avg_sentiment=0.5,
            bullish_count=6,
            bearish_count=2,
            neutral_count=2,
            important_articles=1,
        )
        assert summary.is_bullish is True
        assert summary.is_bearish is False

    def test_is_bearish(self):
        """Test bearish detection."""
        summary = SentimentSummary(
            currency="BTC",
            article_count=10,
            avg_sentiment=-0.4,
            bullish_count=2,
            bearish_count=6,
            neutral_count=2,
            important_articles=1,
        )
        assert summary.is_bearish is True
        assert summary.is_bullish is False

    def test_to_dict(self):
        """Test to_dict serialization."""
        summary = SentimentSummary(
            currency="BTC",
            article_count=10,
            avg_sentiment=0.3,
            bullish_count=5,
            bearish_count=2,
            neutral_count=3,
            important_articles=2,
        )
        d = summary.to_dict()
        assert d["currency"] == "BTC"
        assert d["article_count"] == 10
        assert d["avg_sentiment"] == 0.3
        assert d["is_bullish"] is True


class TestCryptoPanicProvider:
    """Test suite for CryptoPanicProvider."""

    @pytest.fixture
    def config(self) -> CryptoPanicConfig:
        """Create test config."""
        return CryptoPanicConfig(
            api_key="test_key",
            currencies=["BTC", "ETH"],
        )

    @pytest.fixture
    def provider(self, config: CryptoPanicConfig) -> CryptoPanicProvider:
        """Create provider with test config."""
        return CryptoPanicProvider(config)

    def test_init(self, provider: CryptoPanicProvider, config: CryptoPanicConfig):
        """Test provider initialization."""
        assert provider.config == config
        assert provider._client is None
        assert provider._cache == {}

    @pytest.mark.asyncio
    async def test_get_news_disabled(self, config: CryptoPanicConfig):
        """Test get_news when disabled."""
        config.enabled = False
        provider = CryptoPanicProvider(config)
        result = await provider.get_news()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_news_no_api_key(self, config: CryptoPanicConfig):
        """Test get_news without API key."""
        config.api_key = ""
        provider = CryptoPanicProvider(config)
        result = await provider.get_news()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_news_cached(self, provider: CryptoPanicProvider):
        """Test get_news returns cached data."""
        now = datetime.now(timezone.utc)
        cached_article = NewsArticle(
            id="cached",
            title="Cached",
            url="http://test.com",
            source="Test",
            published_at=now,
            currencies=["BTC"],
            kind=NewsKind.NEWS,
        )
        provider._cache["BTC,ETH"] = (now, [cached_article])
        
        result = await provider.get_news()
        assert len(result) == 1
        assert result[0].id == "cached"

    @pytest.mark.asyncio
    async def test_get_sentiment_empty(self, provider: CryptoPanicProvider):
        """Test get_sentiment with no articles."""
        with patch.object(provider, "get_news", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = []
            
            result = await provider.get_sentiment("BTC")
            
            assert result.currency == "BTC"
            assert result.article_count == 0
            assert result.avg_sentiment == 0.0

    @pytest.mark.asyncio
    async def test_get_sentiment_calculates_correctly(self, provider: CryptoPanicProvider):
        """Test sentiment calculation."""
        now = datetime.now(timezone.utc)
        articles = [
            NewsArticle(
                id="1", title="Good", url="http://test.com", source="Test",
                published_at=now, currencies=["BTC"], kind=NewsKind.NEWS,
                sentiment=NewsSentiment.BULLISH,
            ),
            NewsArticle(
                id="2", title="Bad", url="http://test.com", source="Test",
                published_at=now, currencies=["BTC"], kind=NewsKind.NEWS,
                sentiment=NewsSentiment.BEARISH,
            ),
            NewsArticle(
                id="3", title="Neutral", url="http://test.com", source="Test",
                published_at=now, currencies=["BTC"], kind=NewsKind.NEWS,
                sentiment=NewsSentiment.NEUTRAL,
            ),
        ]
        
        with patch.object(provider, "get_news", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = articles
            
            result = await provider.get_sentiment("BTC")
            
            assert result.article_count == 3
            assert result.bullish_count == 1
            assert result.bearish_count == 1
            assert result.neutral_count == 1

    def test_rate_limit_check(self, provider: CryptoPanicProvider):
        """Test rate limiting."""
        now = datetime.now(timezone.utc)
        # Fill up rate limit
        provider._request_timestamps = [now for _ in range(15)]
        
        assert provider._check_rate_limit() is False

    def test_rate_limit_cleans_old(self, provider: CryptoPanicProvider):
        """Test rate limit cleans old timestamps."""
        old = datetime.now(timezone.utc) - timedelta(minutes=5)
        provider._request_timestamps = [old for _ in range(15)]
        
        assert provider._check_rate_limit() is True
        assert len(provider._request_timestamps) == 0

    def test_parse_articles(self, provider: CryptoPanicProvider):
        """Test API response parsing."""
        results = [
            {
                "id": 12345,
                "title": "Bitcoin rises",
                "url": "http://example.com/article",
                "source": {"title": "CoinDesk"},
                "published_at": "2024-01-15T12:00:00Z",
                "currencies": [{"code": "BTC"}],
                "kind": "news",
                "votes": {"positive": 10, "negative": 2, "important": 5},
            }
        ]
        
        articles = provider._parse_articles(results)
        
        assert len(articles) == 1
        assert articles[0].id == "12345"
        assert articles[0].title == "Bitcoin rises"
        assert articles[0].currencies == ["BTC"]
        assert articles[0].votes_positive == 10

    def test_parse_articles_malformed_skipped(self, provider: CryptoPanicProvider):
        """Test that malformed articles are skipped."""
        results = [
            {"id": 1, "title": "Valid"},  # Missing required fields
            {
                "id": 2,
                "title": "Good article",
                "url": "http://test.com",
                "source": {"title": "Source"},
                "published_at": "2024-01-15T12:00:00Z",
                "currencies": [{"code": "ETH"}],
                "kind": "news",
                "votes": {},
            },
        ]
        
        articles = provider._parse_articles(results)
        assert len(articles) == 1
        assert articles[0].id == "2"

    def test_parse_articles_sentiment_bearish(self, provider: CryptoPanicProvider):
        """Test parsing articles with bearish sentiment."""
        results = [
            {
                "id": 1,
                "title": "Market crash",
                "url": "http://test.com",
                "source": {"title": "Source"},
                "published_at": "2024-01-15T12:00:00Z",
                "currencies": [{"code": "BTC"}],
                "kind": "news",
                "votes": {"positive": 1, "negative": 10, "important": 0},
            }
        ]
        
        articles = provider._parse_articles(results)
        assert articles[0].sentiment == NewsSentiment.BEARISH

    def test_parse_articles_sentiment_neutral_more_negative(self, provider: CryptoPanicProvider):
        """Test parsing with slightly more negative votes -> neutral."""
        results = [
            {
                "id": 1,
                "title": "Mixed news",
                "url": "http://test.com",
                "source": {"title": "Source"},
                "published_at": "2024-01-15T12:00:00Z",
                "currencies": [{"code": "ETH"}],
                "kind": "news",
                "votes": {"positive": 4, "negative": 5, "important": 0},
            }
        ]
        
        articles = provider._parse_articles(results)
        assert articles[0].sentiment == NewsSentiment.NEUTRAL

    def test_parse_articles_sentiment_neutral_more_positive(self, provider: CryptoPanicProvider):
        """Test parsing with slightly more positive votes -> neutral."""
        results = [
            {
                "id": 1,
                "title": "Okay news",
                "url": "http://test.com",
                "source": {"title": "Source"},
                "published_at": "2024-01-15T12:00:00Z",
                "currencies": [{"code": "ETH"}],
                "kind": "news",
                "votes": {"positive": 5, "negative": 4, "important": 0},
            }
        ]
        
        articles = provider._parse_articles(results)
        assert articles[0].sentiment == NewsSentiment.NEUTRAL


class TestCryptoPanicProviderAdvanced:
    """Advanced test cases for CryptoPanicProvider."""

    @pytest.fixture
    def config(self) -> CryptoPanicConfig:
        """Create test config."""
        return CryptoPanicConfig(
            api_key="test_key",
            currencies=["BTC", "ETH"],
        )

    @pytest.fixture
    def provider(self, config: CryptoPanicConfig) -> CryptoPanicProvider:
        """Create provider with test config."""
        return CryptoPanicProvider(config)

    @pytest.mark.asyncio
    async def test_context_manager(self, config: CryptoPanicConfig):
        """Test async context manager."""
        async with CryptoPanicProvider(config) as provider:
            assert provider._client is not None
        assert provider._client is None

    @pytest.mark.asyncio
    async def test_get_multi_sentiment(self, provider: CryptoPanicProvider):
        """Test get_multi_sentiment aggregates multiple currencies."""
        with patch.object(provider, "get_sentiment", new_callable=AsyncMock) as mock_get:
            btc_summary = SentimentSummary(
                currency="BTC", article_count=5, avg_sentiment=0.3,
                bullish_count=3, bearish_count=1, neutral_count=1, important_articles=1
            )
            eth_summary = SentimentSummary(
                currency="ETH", article_count=3, avg_sentiment=-0.2,
                bullish_count=1, bearish_count=2, neutral_count=0, important_articles=0
            )
            mock_get.side_effect = [btc_summary, eth_summary]
            
            results = await provider.get_multi_sentiment(["BTC", "ETH"])
            
            assert "BTC" in results
            assert "ETH" in results
            assert results["BTC"].avg_sentiment == 0.3
            assert results["ETH"].avg_sentiment == -0.2

    @pytest.mark.asyncio
    async def test_get_news_rate_limited_returns_stale_cache(self, provider: CryptoPanicProvider):
        """Test that rate-limited requests return stale cache."""
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        cached_article = NewsArticle(
            id="stale",
            title="Stale",
            url="http://test.com",
            source="Test",
            published_at=old_time,
            currencies=["BTC"],
            kind=NewsKind.NEWS,
        )
        provider._cache["BTC,ETH"] = (old_time, [cached_article])
        
        # Fill rate limit
        now = datetime.now(timezone.utc)
        provider._request_timestamps = [now for _ in range(15)]
        
        result = await provider.get_news(use_cache=False)
        
        assert len(result) == 1
        assert result[0].id == "stale"

    @pytest.mark.asyncio
    async def test_get_news_rate_limited_no_cache(self, provider: CryptoPanicProvider):
        """Test rate-limited with no cache returns empty."""
        now = datetime.now(timezone.utc)
        provider._request_timestamps = [now for _ in range(15)]
        
        result = await provider.get_news(use_cache=False)
        
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_news_without_client(self, provider: CryptoPanicProvider):
        """Test _fetch_news creates temporary client when none exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 999,
                    "title": "Test",
                    "url": "http://test.com",
                    "source": {"title": "Source"},
                    "published_at": "2024-01-15T12:00:00Z",
                    "currencies": [{"code": "BTC"}],
                    "kind": "news",
                    "votes": {},
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client
            
            result = await provider._fetch_news(["BTC"])
            
            assert len(result) == 1
            assert result[0].id == "999"

    @pytest.mark.asyncio
    async def test_do_fetch_with_filter_kind(self, config: CryptoPanicConfig):
        """Test _do_fetch includes filter_kind in params."""
        config.filter_kind = NewsKind.MEDIA
        provider = CryptoPanicProvider(config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        await provider._do_fetch(mock_client, ["BTC"])
        
        call_args = mock_client.get.call_args
        assert call_args[1]["params"]["kind"] == "media"

    @pytest.mark.asyncio
    async def test_do_fetch_non_200_returns_empty(self, provider: CryptoPanicProvider):
        """Test _do_fetch returns empty on non-200 response."""
        mock_response = MagicMock()
        mock_response.status_code = 429  # Rate limited
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        result = await provider._do_fetch(mock_client, ["BTC"])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_do_fetch_http_error(self, provider: CryptoPanicProvider):
        """Test _do_fetch handles HTTP errors gracefully."""
        import httpx
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
        
        result = await provider._do_fetch(mock_client, ["BTC"])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_do_fetch_json_error(self, provider: CryptoPanicProvider):
        """Test _do_fetch handles JSON parse errors."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        
        result = await provider._do_fetch(mock_client, ["BTC"])
        
        assert result == []


class TestNewsArticleSentimentScore:
    """Additional tests for NewsArticle sentiment_score property."""

    def test_sentiment_score_bullish(self):
        """Test bullish sentiment score."""
        article = NewsArticle(
            id="1", title="Test", url="http://test.com", source="Test",
            published_at=datetime.now(timezone.utc), currencies=["BTC"],
            kind=NewsKind.NEWS, sentiment=NewsSentiment.BULLISH,
        )
        assert article.sentiment_score == 0.5

    def test_sentiment_score_neutral(self):
        """Test neutral sentiment score."""
        article = NewsArticle(
            id="1", title="Test", url="http://test.com", source="Test",
            published_at=datetime.now(timezone.utc), currencies=["BTC"],
            kind=NewsKind.NEWS, sentiment=NewsSentiment.NEUTRAL,
        )
        assert article.sentiment_score == 0.0

    def test_sentiment_score_bearish(self):
        """Test bearish sentiment score."""
        article = NewsArticle(
            id="1", title="Test", url="http://test.com", source="Test",
            published_at=datetime.now(timezone.utc), currencies=["BTC"],
            kind=NewsKind.NEWS, sentiment=NewsSentiment.BEARISH,
        )
        assert article.sentiment_score == -0.5

