CREATE TABLE users
(
    id        serial PRIMARY KEY,
    password  bytea       not null,
    email     varchar(40) not null,
    firstname varchar(40) not null,
    lastname  varchar(40) not null,
    createdAt timestamp   not null default now(),

    CONSTRAINT users_email_uniq UNIQUE (email)
);

CREATE TYPE physical_item_status AS enum ('registered', 'handed in', 'processing', 'processed');

CREATE TABLE physical_items
(
    id          serial PRIMARY KEY,
    serial      varchar(64)          not null,
    description varchar(2000)        not null default '',
    length      int                  not null,
    width       int                  not null,
    height      int                  not null,
    weight      float                not null,

    authToken   varchar(64)          not null,
    status      physical_item_status not null default 'registered',

    createdAt   timestamp            not null default now(),

    CONSTRAINT physical_items_serial_uniq UNIQUE (serial)
);

CREATE TABLE physical_item_ownerships
(
    physicalItemId int not null,
    userId         int not null,

    PRIMARY KEY (physicalItemId, userId),
    FOREIGN KEY (physicalItemId) REFERENCES physical_items (id) ON DELETE CASCADE,
    FOREIGN KEY (userId) REFERENCES users (id) ON DELETE CASCADE
);

comment on column physical_items.length is 'length of the item in cm';
comment on column physical_items.width is 'width of the item in cm';
comment on column physical_items.height is 'height of the item in cm';
comment on column physical_items.weight is 'weight of the item in cm';

CREATE TYPE digital_item_status AS enum ('uploaded', 'processing', 'processed');

create table digital_items
(
    id          serial PRIMARY KEY,
    name        varchar(100)        not null,
    description varchar(2000)       not null default '',
    authToken   varchar(64)         not null,
    status      digital_item_status not null default 'uploaded',
    size        integer             not null,

    content     bytea               not null,

    createdAt   timestamp           not null default now()
);

comment on column digital_items.size is 'size of the content in bytes';

CREATE TABLE digital_item_ownerships
(
    digitalItemId int not null,
    userId        int not null,

    PRIMARY KEY (digitalItemId, userId),
    FOREIGN KEY (digitalItemId) REFERENCES digital_items (id) ON DELETE CASCADE,
    FOREIGN KEY (userId) REFERENCES users (id) ON DELETE CASCADE
);

CREATE TABLE analysis_result
(
    id serial PRIMARY KEY,
    digitalItemId int not null,
    "type" varchar(15) not null,
    result bytea not null,
    FOREIGN KEY (digitalItemId) REFERENCES digital_items (id) ON DELETE CASCADE
);

CREATE TABLE faq
(
    id       serial PRIMARY KEY,
    question varchar(100)   not null,
    answer   varchar(10000) not null
);

INSERT INTO faq (question, answer)
VALUES ('How do you recycle e-waste?',
        'Our plant is fully powered by a team of robots called <strong>W.I.E.N.</strong> short for <strong>Waste Inspector Electronic Navigators</strong>. Created from recycled waste, they are doing their job with the expected professionalism. They are programmed to scan your items in less than a minute and determine the exact compound. The items are then sent to the department of reconstruction. Other robots dismount the goods and send the ingredients to other departments depending on the recovered materials.'),
       ('What about digital waste?',
       'Digital waste, such as compressed archives, will be processed by the <strong>Deep hOlistic Neuro-Data EntanglEment Scalable Tensor Array</strong> unit (internally referenced by our employees as <strong>DONDEESTA</strong> for the sake of brevity). The purpose of DONDEESTA is to subsume the knowledge extrapolated from all uploaded files and restructure it to be easily accessible. Unfortunately, given the extremely complicated architecture of the system, digital waste is only stored at the moment without being further processed. We will inform you whenever DONDEESTA becomes operational.'),
       ('How much digital data can I upload at once?',
       'Please refer to the limits specified in the recycle page.'),
       ('How is my contribution valuable to our community?',
       'With all the knowledge we receive from digital waste, we plan to create an open system where people will be able to find all the information collected by our ancestors. It can help us rebuild society way faster than currently expected and avoid the mistakes previously made by humanity. Concerning recycling of e-waste, we plan to produce new devices by fully recycling electronic junk. This is not simply advisable but comes out of necessity since natural resources on the planet have been fully exploited by previous generations.'),
       ('Who is running the waste recycling company?',
       'Two persons who care about their community. You can read more in the <a href="/about">about</a> page.'),
       ('How can I help even further?',
       'Robots and drones mostly operate the plant. However, we always need talented people to develop more efficient algorithms and fix some seldom major breakage (the robots themselves can fix minor issues). You can also file a <a href="%REPORT_APP_URL%">bug report</a> if you find a vulnerability that affects the Web interface.');