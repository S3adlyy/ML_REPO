const form = document.getElementById('auth-form');
const config = JSON.parse(document.getElementById('firebase-config').textContent);
const errorBox = document.getElementById('auth-error');
const submit = document.getElementById('auth-submit');
const reset = document.getElementById('reset-password');
const show = (message) => { errorBox.textContent = message; errorBox.hidden = false; };
document.getElementById('toggle-password').addEventListener('click', e => {
  const field = form.elements.password;
  field.type = field.type === 'password' ? 'text' : 'password';
  e.target.textContent = field.type === 'password' ? 'Afficher' : 'Masquer';
  e.target.setAttribute('aria-label', field.type === 'password' ? 'Afficher le mot de passe' : 'Masquer le mot de passe');
});
let sdkPromise;
function sdk() {
  if (!sdkPromise) sdkPromise = Promise.all([
    import('https://www.gstatic.com/firebasejs/11.6.0/firebase-app.js'),
    import('https://www.gstatic.com/firebasejs/11.6.0/firebase-auth.js')
  ]).then(async ([app, api]) => {
    const auth = api.getAuth(app.initializeApp(config));
    await api.setPersistence(auth, api.inMemoryPersistence);
    return {auth, api};
  }).catch(error => { sdkPromise = null; throw error; });
  return sdkPromise;
}
const errors = {
  'auth/email-already-in-use': 'Cette adresse est déjà utilisée. Connectez-vous ou réinitialisez votre mot de passe.',
  'auth/invalid-credential': 'Adresse e-mail ou mot de passe incorrect.',
  'auth/invalid-email': 'Vérifiez votre adresse e-mail.',
  'auth/weak-password': 'Choisissez un mot de passe plus long et plus robuste.',
  'auth/password-does-not-meet-requirements': 'Ce mot de passe ne respecte pas les exigences du service. Ajoutez des majuscules, chiffres et caractères spéciaux.',
  'auth/too-many-requests': 'Trop de tentatives. Patientez avant de réessayer.',
  'auth/network-request-failed': 'Connexion interrompue. Vérifiez votre accès à Internet.',
  'auth/operation-not-allowed': 'La connexion par e-mail doit être activée dans Firebase.'
};
let pendingSignupUser;
form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const label = submit.textContent;
  submit.disabled = true; submit.textContent = 'Connexion en cours…'; errorBox.hidden = true;
  try {
    const {auth, api} = await sdk();
    let user;
    if (form.dataset.mode === 'signup') {
      if (pendingSignupUser && pendingSignupUser.email === form.elements.email.value.trim()) user = pendingSignupUser;
      else user = (await api.createUserWithEmailAndPassword(auth, form.elements.email.value.trim(), form.elements.password.value)).user;
      pendingSignupUser = user;
      await api.updateProfile(user, {displayName: form.elements.name.value.trim()});
    } else user = (await api.signInWithEmailAndPassword(auth, form.elements.email.value.trim(), form.elements.password.value)).user;
    const idToken = await user.getIdToken(true);
    const response = await fetch(form.dataset.endpoint, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value}, body: JSON.stringify({idToken})});
    const result = await response.json();
    if (!response.ok) { show(result.error || 'Connexion indisponible. Réessayez.'); return; }
    await api.signOut(auth);
    window.location.assign(result.redirect);
  } catch (error) { show(errors[error.code] || 'Connexion indisponible. Vérifiez votre réseau et réessayez.'); }
  finally { submit.disabled = false; submit.textContent = label; }
});
reset?.addEventListener('click', async () => {
  if (!form.elements.email.reportValidity()) return;
  reset.disabled = true;
  try {
    const {auth, api} = await sdk();
    await api.sendPasswordResetEmail(auth, form.elements.email.value.trim());
    show('Si un compte correspond à cette adresse, un e-mail de réinitialisation vous sera envoyé.');
  } catch (error) { show(errors[error.code] || 'Impossible d’envoyer la demande. Réessayez.'); }
  finally { reset.disabled = false; }
});
