# Deploy Prisma to Render

## Free demo resources

- Free Python web service and free PostgreSQL in Frankfurt; no paid instance plans.
- The web service sleeps after 15 idle minutes and can take about a minute to wake.
- Free PostgreSQL expires after 30 days; demo profiles/history must be exported before expiration if needed.
- Free web instances share the workspace's 750 monthly hours. Existing services also consume this allowance.
- One synchronous Gunicorn worker avoids duplicate model caches. The 512 MB memory limit needs live verification with all six models; no paid upgrade is authorized.
- Automatic deployment is disabled; deploy approved changes manually.

Source: https://render.com/docs/free

## Model distribution

The seven current `.joblib` files are bundled without retraining or reserializing. The bundle is approximately 52.5 MiB compressed. `ml_models/deployment-manifest.json` pins the bundle and each file with SHA-256 hashes. Builds reject missing, changed, unexpected, or corrupted artifacts and exercise all six adapters before deployment.

The user approved publishing `prisma-models-v1.zip` as the public `models-v1` GitHub release. Its URL is configured in the Blueprint. Do not commit credentials or signed URLs. The package has only model files, no Firebase credentials, `.env`, profiles, or database records.

Repackage future approved model updates with:

```sh
python scripts/package_models.py --output /path/outside/repo/prisma-models-v1.zip
```

Review and commit the changed manifest together with any adapter/dependency updates.

## Deployment steps

1. Review and merge the deployment pull request, or explicitly select its branch in Render.
2. In Render, choose New → Blueprint and select `S3adlyy/ML_REPO`. Verify both resources show the Free plan before applying.
3. Supply `FIREBASE_API_KEY` when prompted. The other public Firebase settings are in the Blueprint. Render generates `DJANGO_SECRET_KEY` and connects `DATABASE_URL` automatically.
4. Add a Render secret file named `firebase-service-account.json` containing the existing Firebase service-account JSON. `GOOGLE_APPLICATION_CREDENTIALS` points to `/etc/secrets/firebase-service-account.json`. Never commit the key to GitHub. Upload it before accepting sign-ups.
5. Run a manual deployment. The build installs dependencies, verifies/downloads model files, collects static files, and runs six model smoke checks. Startup applies database migrations and starts Gunicorn.
6. Add the final `*.onrender.com` hostname to Firebase Authentication → Settings → Authorized domains. Django accepts `RENDER_EXTERNAL_HOSTNAME` and trusts its HTTPS origin automatically. For a custom domain, also configure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.
7. Confirm `/health/`, static styles, signup/signin, onboarding, all six model results, history isolation, and data persistence after a redeploy. Share the final HTTPS URL with the team.

The online database starts empty; existing local profiles/history are not uploaded. Firebase users can sign in and complete their online profile. Public landing pages and prediction forms remain accessible without login, matching current behavior. This deployment does not add a team allowlist.

## Environment and model limitation

Python 3.13 and existing ML package versions remain pinned. All six real adapters pass locally under the existing environment. The capital artifact was serialized with scikit-learn 1.9.1 while this app uses 1.8.0; upgrading the shared dependency without checking the other models would be unsafe. The build smoke test detects execution failures but does not establish statistical equivalence. Align/re-export all team artifacts from one agreed environment before treating results as production-grade. No models have been retrained or modified here.

## Local checks

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
.venv/bin/python manage.py test portal --noinput
.venv/bin/python scripts/fetch_models.py
.venv/bin/python scripts/smoke_models.py
```

Production requires a real `DATABASE_URL` and a strong `DJANGO_SECRET_KEY`. Keep `.env` local. Local development continues to use SQLite and the existing Firebase key path.
