# Prisma product experience

The Django app now includes a public landing page, email/password sign-up and sign-in, password reset, a three-stage onboarding flow, a personal dashboard, reusable profile answers, module filtering, selected interests, and recent analysis results. Existing prediction routes and adapters remain available for public exploration.

## Activate Firebase

1. In Firebase Console, create/select your project and register a Web app.
2. In Authentication → Sign-in method, enable Email/Password. Configure a password policy (the signup UI requires at least 8 characters). Enable email enumeration protection.
3. Add your development and production hosts under Authentication → Settings → Authorized domains. Use HTTPS in production.
4. Copy the public web configuration into environment variables from `.env.example`: `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_PROJECT_ID`, `FIREBASE_APP_ID`.
5. Configure server credentials with `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service-account JSON file stored outside the repository, or use Application Default Credentials on your host with `FIREBASE_USE_APPLICATION_DEFAULT_CREDENTIALS=1`. Do not put this key in frontend code or commit it.
6. Put your configuration in the ignored `.env` file in the project root. Django loads it automatically; existing process environment variables take precedence. The supplied SyncAura public web configuration is already saved locally. The server credential path has been configured locally and a live Firebase Admin read succeeded. Email/Password is enabled in the project. Use `http://localhost:8000` locally because `localhost` is an authorized Firebase domain. Live account creation and password-reset email delivery have not been performed as part of automated QA.
7. Install dependencies and migrate:

```sh
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Without Firebase configuration the public website and model forms work, while account submission is visibly unavailable. No fake sign-in is provided. Live email delivery, account creation and verification must be checked against your configured Firebase project.

## Data and authentication

Firebase handles passwords. The browser exchanges a freshly issued ID token for a Django session. The backend verifies the signature, project, expiration, revocation status, and recent authentication using Firebase Admin. Accounts are keyed by Firebase UID, never merged by email. Firebase tokens are held only in memory on the client and are not saved in Django. CSRF protects the exchange, profile saves, history clearing, and logout. Django sessions expire after one hour; revocation is checked at sign-in, not on each subsequent Django request. Set `DJANGO_DEBUG=0`, a strong `DJANGO_SECRET_KEY`, and explicit `DJANGO_ALLOWED_HOSTS` for deployment; secure cookies are enabled outside debug mode. Apply your host's authentication rate limits before public deployment.

Profiles and analysis labels are stored in the Django database. Profile consent is required to save onboarding answers; financial inputs are optional. Sensitive model-specific fields are not collected in onboarding. Compatible saved answers prefill only the input fields declared by each module, never its target. Prediction requests save only the result label, module and timestamp for signed-in users; scenario inputs are not copied into history. Users can edit their profile and clear their own history.

The existing `.joblib` artifacts were not retrained or modified. Some capital artifacts emit scikit-learn 1.9.1-versus-1.8.0 compatibility warnings in the existing environment; align training and inference environments before production.

## Validation

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py test portal --noinput
```

Account tests mock the Firebase verification boundary; they do not claim a live Firebase connection. They cover rejected tokens, stale authentication, CSRF, identity separation, onboarding validation, target exclusion, private history, and result persistence.

Firebase references: https://firebase.google.com/docs/auth/admin/verify-id-tokens and https://firebase.google.com/docs/auth/web/password-auth
