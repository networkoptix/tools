-- Create and fill `run_kind` table

CREATE TABLE public.run_kind (
    id integer NOT NULL PRIMARY KEY,
    name text NOT NULL,
    order_num integer NOT NULL);

ALTER TABLE public.run_kind OWNER TO postgres;

INSERT INTO public.run_kind  (id, name, order_num)
VALUES
 (1, 'voting_for_build', 1),
 (2, 'voting_for_test', 50);

 CREATE SEQUENCE public.run_kind_id_seq
    AS integer
    START WITH 4
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


UPDATE public.test SET description = 'Build' where path = 'build';
UPDATE public.test SET description = 'Unit tests' where path = 'unit';
UPDATE public.test SET description = 'Functional tests' where path = 'functional';
UPDATE public.test SET description = 'Real camera tests' where path = 'cameratest';
UPDATE public.test SET description = 'SDK unit tests' where path = 'sdk_unit';
UPDATE public.test SET description = 'Scalability tests' where path = 'scalability';



