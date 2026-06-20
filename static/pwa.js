let deferredPrompt;
const installButton = document.getElementById('install-app-button');

window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  deferredPrompt = event;

  if (installButton) {
    installButton.style.display = 'inline-flex';
    installButton.addEventListener('click', async () => {
      installButton.style.display = 'none';
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      deferredPrompt = null;
      console.log('User choice:', choiceResult.outcome);
    });
  }
});

window.addEventListener('appinstalled', () => {
  console.log('PWA installed');
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', async () => {
    try {
      await navigator.serviceWorker.register('/sw.js');
      console.log('Service worker registered successfully.');
    } catch (error) {
      console.error('Service worker registration failed:', error);
    }
  });
}
