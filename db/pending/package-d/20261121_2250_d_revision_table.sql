CREATE TABLE revision (
    revision_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    floor_id    bigint NOT NULL REFERENCES floor ON DELETE CASCADE,
    rev_no      int NOT NULL,
    parent_id   bigint REFERENCES revision,
    upload_id   bigint UNIQUE REFERENCES upload,
    created_by  bigint NOT NULL REFERENCES app_user,
    state       text NOT NULL DEFAULT 'draft' CHECK (state IN ('draft','in_review','approved')),
    created_at  timestamptz NOT NULL DEFAULT now(),
    approved_at timestamptz,
    UNIQUE (floor_id, rev_no),
    CHECK ((state = 'approved') = (approved_at IS NOT NULL))
);
