-- Verbatim DDL of the pinned source (hadith-kg.db), used to build test fixtures.

CREATE TABLE alems (                   -- hadith critics (أئمة الجرح والتعديل)
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  nickname TEXT,
  shuhra TEXT NOT NULL,
  laqab TEXT,
  tabaka INTEGER NOT NULL,
  death_year INTEGER NOT NULL,
  rank_no INTEGER NOT NULL,
  rank TEXT,
  aqwal_qty INTEGER NOT NULL,
  notes TEXT
);

CREATE TABLE aqwal (                   -- jarh wa ta'dil statements: alem on rawi
  id INTEGER PRIMARY KEY,
  alem_id INTEGER NOT NULL REFERENCES alems(id),
  rawi_id INTEGER NOT NULL REFERENCES rawis(id),
  qawl TEXT NOT NULL
);

CREATE TABLE books (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  author_no INTEGER NOT NULL,          -- author id in the alem/author numbering of the source
  author_name TEXT NOT NULL,
  author_death_year INTEGER,
  city TEXT, dar TEXT, tabaa TEXT,     -- edition info
  tasnif_no INTEGER NOT NULL,          -- book category (1=صحاح ومستخرجات ...)
  tasnif TEXT NOT NULL,
  hadith_qty INTEGER NOT NULL
);

CREATE TABLE hadiths (
  id INTEGER PRIMARY KEY,
  book_id INTEGER NOT NULL REFERENCES books(id),
  no_inbook INTEGER NOT NULL,
  page_no INTEGER NOT NULL,
  type_no INTEGER NOT NULL,            -- 0=قدسي 1=مرفوع 2=موقوف 3=مقطوع
  type TEXT NOT NULL,
  matn_no INTEGER NOT NULL,            -- hukm code
  matn TEXT NOT NULL,                  -- hukm label (صحيح / حسن / ضعيف ...)
  group_id INTEGER,                    -- meaning group; NULL for موقوف/مقطوع
  takhrij INTEGER,                     -- narration-route cluster within the group
  taraf_nass TEXT,                     -- missing for 3 source rows
  nass TEXT NOT NULL,                  -- PLAIN text of the full hadith (sanad + matn)
  matn_start INTEGER, matn_end INTEGER -- offsets of the matn (span.nass) in nass
);

CREATE TABLE hadith_rawis (            -- inline narrator mentions, in text order
  hadith_id INTEGER NOT NULL REFERENCES hadiths(id),
  seq INTEGER NOT NULL,                -- 0-based order of appearance
  rawi_id INTEGER,                     -- NULL = malformed source href that could not be
                                       -- repaired from the sanad chain; a few ids also
                                       -- have no rawis row (source quirk, kept as-is)
  start INTEGER NOT NULL, end INTEGER NOT NULL,
  PRIMARY KEY (hadith_id, seq)
) WITHOUT ROWID;

CREATE TABLE meaning_groups (          -- one row = one hadith "meaning" (source: cat table)
  id INTEGER PRIMARY KEY,
  taraf_id INTEGER,                    -- representative taraf
  is_qudsi INTEGER NOT NULL,
  matn_no INTEGER NOT NULL,            -- overall hukm (0=صحيح 1=حسن 2=ضعيف 3=شديد الضعف ...)
  sahaba_qty INTEGER NOT NULL,         -- distinct companions narrating this meaning (source-computed)
  repeat_qty INTEGER NOT NULL,         -- total occurrences across books (source-computed)
  nass TEXT NOT NULL                   -- normalized taraf text of the meaning
);

CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE rawis (                   -- narrators
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  nickname TEXT NOT NULL,
  rank_no INTEGER NOT NULL,
  rank TEXT,                           -- ثقة / صدوق / ضعيف / صحابي ...
  tabaka INTEGER NOT NULL,             -- generation layer
  is_bukhari INTEGER NOT NULL,         -- narrated in Sahih al-Bukhari
  is_muslim INTEGER NOT NULL,
  has_ikhtilat INTEGER NOT NULL,
  has_tadlis INTEGER NOT NULL,
  riwaya_qty INTEGER NOT NULL,
  birth_year INTEGER,                  -- parsed when unambiguous, else NULL
  birth_year_raw TEXT,                 -- source string (may be a range like "40 - 20")
  death_year INTEGER,
  death_year_raw TEXT,
  age_raw TEXT,
  profession TEXT, nasab TEXT, iqama TEXT, death_place TEXT
, is_stub INTEGER NOT NULL DEFAULT 0);

CREATE TABLE sanads (                  -- one isnad (chain) of one hadith
  id INTEGER PRIMARY KEY,
  hadith_id INTEGER NOT NULL REFERENCES hadiths(id),
  matn_no INTEGER NOT NULL,
  matn TEXT NOT NULL,                  -- hukm label for this chain
  hukum TEXT NOT NULL,                 -- full hukm sentence on the isnad
  group_id INTEGER,                    -- meaning group (= hadith's)
  takhrij INTEGER,
  max_rank INTEGER,                    -- weakest narrator's rank_no in the chain (from source)
  length INTEGER                       -- chain length incl. author
);

CREATE TABLE sanad_rawis (             -- the chain itself
  sanad_id INTEGER NOT NULL REFERENCES sanads(id),
  pos INTEGER NOT NULL,                -- 0 = book author, ascending toward the sahabi
  rawi_id INTEGER NOT NULL REFERENCES rawis(id),
  PRIMARY KEY (sanad_id, pos)
) WITHOUT ROWID;

CREATE TABLE topics (                  -- موضوعات tree (nested set + parent)
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  parent_id INTEGER,                   -- NULL for root
  level INTEGER NOT NULL,
  lft INTEGER NOT NULL, rgt INTEGER NOT NULL,
  tree_id INTEGER NOT NULL,
  group_id INTEGER                     -- leaf link to meaning_groups (source field: takhrij)
);
