# AgentQ - Portfolio Management System

## Architecture Overview

```
20260321_portfolio upgrade v3/
├── app/                    # Application layer
│   ├── bot.py             # Discord bot entry point
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── models/            # Domain models
│   ├── schemas/            # Data schemas
│   ├── services/           # Business services
│   └── utils/             # Utility functions
├── features/              # Feature modules
│   ├── portfolio/         # Portfolio management
│   ├── quant/            # Quantitative analysis
│   ├── finance/          # Financial analysis
│   ├── screener/         # Stock screening
│   ├── ai/              # AI services
│   └── industry/         # Industry mapping
├── infrastructure/        # Infrastructure layer
│   ├── database/         # Database models & connection pool
│   ├── cache/            # Caching layer
│   └── external/          # External API adapters
├── config/               # Configuration
└── tests/                # Tests
```

## Scalability Features

### 1. Database Connection Pooling
- Configurable pool size (default: 20 connections)
- Max overflow: 40 additional connections
- Connection recycling every hour
- Pre-ping for connection health checks

### 2. Caching Layer
- In-memory cache with TTL support
- Thread-safe implementation
- Cache key prefixing for organization
- Decorator support for easy caching

### 3. Stateless Design
- All user state stored in database
- No in-memory session data
- Horizontal scaling ready

### 4. Async Support
- All I/O operations are async-ready
- Database queries use connection pool
- External API calls are non-blocking

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp config/.env.example config/.env
# Edit config/.env with your credentials
```

3. Run the bot:
```bash
python main.py
```

## Commands

- `!menu` - Show main menu
- `@bot` - Show main menu (when mentioned)

## Modules

### Portfolio Module (`features/portfolio/`)
- `service.py` - Core business logic
- `repository.py` - Data access layer
- `risk_engine.py` - Risk calculations
- `discord_ui.py` - Discord UI components

### Infrastructure
- `infrastructure/database/` - SQLAlchemy models & connection pool
- `infrastructure/cache/` - Caching utilities
- `infrastructure/external/` - External API adapters

## Performance Tuning

For 100k+ users:

1. **Database**: Use PostgreSQL with connection pooling
2. **Cache**: Enable Redis for distributed caching
3. **Workers**: Run multiple bot instances behind a load balancer
4. **Rate Limiting**: Implement API rate limiting

## License

Proprietary - Buytrend/Vnstock
