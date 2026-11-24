# Deploying to Google Cloud

## App Engine

`deploy/app.yaml` serves `dist/` as static files over HTTPS, with `/` mapped to `index.html` and
`.mjs` files served as JavaScript.

```sh
gcloud auth login
npm run build
GCP_PROJECT=<project-id> npm run deploy:gcloud
```

The first deploy to a project asks you to pick an App Engine region. The site is then at
`https://<project-id>.<region-code>.r.appspot.com`.

## Cloud Storage

```sh
gsutil mb gs://<bucket>
gsutil iam ch allUsers:objectViewer gs://<bucket>
gsutil web set -m index.html gs://<bucket>
npm run build && gsutil -m rsync -r -d dist gs://<bucket>
```

The page is at `https://storage.googleapis.com/<bucket>/index.html`. Module scripts must be served
as JavaScript, so if `.mjs` files upload with a generic type, fix them with

```sh
gsutil -m setmeta -h "Content-Type:text/javascript" "gs://<bucket>/**.mjs"
```
