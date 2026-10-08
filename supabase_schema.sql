create table if not exists public.found_items (
    item_name text primary key,
    location text not null,
    ciphertext text not null,
    iv text not null,
    timestamp text not null
);

alter table public.found_items enable row level security;