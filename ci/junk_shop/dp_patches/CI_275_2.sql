-- Rename tests, use short bundle name in the `test.path` and `run.name`
DO $$
DECLARE
   m   varchar[];
   arr varchar[] := array[
     ['unit', 'ut'],
     ['functional', 'ft'],
     ['cameratest', 'rct'],
     ['sdk_unit', 'sdk']];
BEGIN
   FOREACH m SLICE 1 IN ARRAY arr
   LOOP
      UPDATE public.test SET path = regexp_replace(path, '^' || m[1], m[2]) where position(m[1] IN path) = 1;
      UPDATE public.run SET name = m[2] where name = m[1];
   END LOOP;
END $$;