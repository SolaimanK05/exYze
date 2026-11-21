CREATE TABLE project (
    project_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_id     bigint NOT NULL REFERENCES app_user,
    client_id    bigint REFERENCES app_user,
    name         text NOT NULL,
    site_address text,
    created_at   timestamptz NOT NULL DEFAULT now()
);
