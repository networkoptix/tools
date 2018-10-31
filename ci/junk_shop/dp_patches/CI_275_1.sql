-- Create and fill `run_kind` table

CREATE TABLE public.run_kind (
    id integer NOT NULL PRIMARY KEY,
    name text NOT NULL,
    order_num integer NOT NULL);

ALTER TABLE public.run_kind OWNER TO postgres;

INSERT INTO public.run_kind  (id, name, order_num)
VALUES
 (1, 'production', 1),
 (2, 'test', 100);

 CREATE SEQUENCE public.run_kind_id_seq
    AS integer
    START WITH 3
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE public.run_kind_id_seq OWNER TO postgres;

ALTER SEQUENCE public.run_kind_id_seq OWNED BY public.run_kind.id;

ALTER TABLE ONLY public.run_kind ALTER COLUMN id SET DEFAULT nextval('public.run_kind_id_seq'::regclass);

-- Modify `run` table
-- Add columns
--   `run.description` - description from jenkins job
--   `run.jenkins_url` - jenkins URL for the run
--   `run.revision`    - NX VMS revision number
--   `run.kind`        - run kind (Production, Test, etc)
ALTER TABLE public.run
  ADD COLUMN IF NOT EXISTS description text,
  ADD COLUMN IF NOT EXISTS jenkins_url text,
  ADD COLUMN IF NOT EXISTS revision text,
  ADD COLUMN IF NOT EXISTS kind integer;

-- Set `run.kind` to `Production` for exist runs
UPDATE public.run SET kind = 1 where root_run is NULL;

ALTER TABLE public.run
  ADD CONSTRAINT
    fk_run__kind FOREIGN KEY (kind) REFERENCES public.run_kind(id);

CREATE INDEX IF NOT EXISTS idx_run__kind ON public.run(kind);

-- Modify `test` table
-- Add & fill `test.description`

ALTER TABLE public.test
  ADD COLUMN IF NOT EXISTS description text;

DO $$
DECLARE
   m   varchar[];
   arr varchar[] := array[
     ['build','Build'],
     ['unit', 'Unit tests'],
     ['functional', 'Functional tests'],
     ['cameratest', 'Real camera tests'],
     ['sdk_unit', 'SDK unit tests'],
     ['scalability', 'Scalability tests']];
BEGIN
   FOREACH m SLICE 1 IN ARRAY arr
   LOOP
      UPDATE public.test SET description = m[2] where path = m[1];
   END LOOP;
END $$;



