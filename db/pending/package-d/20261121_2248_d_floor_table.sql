CREATE TABLE floor (
    floor_id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id       bigint NOT NULL REFERENCES project ON DELETE CASCADE,
    level_no         int NOT NULL,
    name             text NOT NULL,
    default_height_m numeric(4,2) NOT NULL DEFAULT 3.00 CHECK (default_height_m > 0),
    UNIQUE (project_id, level_no)
);
