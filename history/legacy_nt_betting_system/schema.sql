PRAGMA foreign_keys = ON;

-- Main bets table
CREATE TABLE IF NOT EXISTS bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    match TEXT NOT NULL,
    selection TEXT NOT NULL,
    decimal_odds REAL NOT NULL,
    stake_nok REAL NOT NULL,
    result TEXT NOT NULL CHECK(result IN ('Pending', 'Win', 'Loss', 'Void')),
    p_l_nok REAL,
    sport TEXT,
    league TEXT,
    market_type TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bets_result ON bets(result);
CREATE INDEX IF NOT EXISTS idx_bets_date ON bets(date);
CREATE INDEX IF NOT EXISTS idx_bets_sport ON bets(sport);

-- Bankroll history
CREATE TABLE IF NOT EXISTS bankroll_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    equity_nok REAL NOT NULL,
    pending_at_risk REAL NOT NULL DEFAULT 0,
    note TEXT
);