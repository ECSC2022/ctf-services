CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
	displayname TEXT NOT NULL,
    address TEXT,
    is_address_public BOOLEAN DEFAULT FALSE NOT NULL,
    telephone_number TEXT,
    is_telephone_number_public BOOLEAN DEFAULT FALSE NOT NULL,
    status TEXT,
    is_status_public BOOLEAN DEFAULT FALSE NOT NULL
);

CREATE TABLE offers (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    picture TEXT,
    timestamp TIMESTAMP NOT NULL DEFAULT now(),
    creator_id INTEGER NOT NULL,
    owner_id INTEGER,
    FOREIGN KEY (creator_id) REFERENCES profiles (id),
    FOREIGN KEY (owner_id) REFERENCES profiles (id)
);

CREATE TABLE requests (
    id SERIAL PRIMARY KEY,
    offer_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT now(),
    -- request_status INTEGER DEFAULT 0 NOT NULL, -- NEW = 0, ACCEPTED = 1, REJECTED = 2
    FOREIGN KEY (offer_id) REFERENCES offers (id),
    FOREIGN KEY (user_id) REFERENCES profiles (id),
    UNIQUE (offer_id, user_id)
);
