-- Passport scans. This is sensitive identity data, so the bucket is private:
-- there is no public URL, and every read goes through a short-lived signed URL
-- that the policies below have to authorise first.
--
-- Layout is <auth user id>/passport.<ext>. The first path segment is the
-- ownership check, which is why it must be the uid and not anything the user
-- can choose.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'passports', 'passports', false,
  5242880,                                   -- 5 MB
  array['image/jpeg', 'image/png', 'application/pdf']
)
on conflict (id) do update
set public             = excluded.public,
    file_size_limit    = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

-- Owner reads their own file; an admin reads any of them.
create policy passports_read on storage.objects
  for select to authenticated
  using (
    bucket_id = 'passports'
    and (
      (select auth.uid())::text = (storage.foldername(name))[1]
      or (select private.is_admin())
    )
  );

-- Uploads are confined to the caller's own folder. Admins are deliberately
-- left out: staff should not be able to plant a document under a customer's
-- identity.
create policy passports_insert on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'passports'
    and (select auth.uid())::text = (storage.foldername(name))[1]
  );

-- Replacing a file is an upsert, which needs UPDATE alongside INSERT and
-- SELECT; with INSERT alone the replace fails silently.
create policy passports_update on storage.objects
  for update to authenticated
  using (
    bucket_id = 'passports'
    and (select auth.uid())::text = (storage.foldername(name))[1]
  )
  with check (
    bucket_id = 'passports'
    and (select auth.uid())::text = (storage.foldername(name))[1]
  );

create policy passports_delete on storage.objects
  for delete to authenticated
  using (
    bucket_id = 'passports'
    and (select auth.uid())::text = (storage.foldername(name))[1]
  );
