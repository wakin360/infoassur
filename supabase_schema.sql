-- Keep searchable item details with encrypted proof; never store the proof as plaintext.
create table if not exists public.found_items (
    item_name text primary key,
    location text not null,
    ciphertext text not null,
    iv text not null,
    timestamp text not null
);

-- Require database access policies for client roles; the server uses its private service key.
alter table public.found_items enable row level security;