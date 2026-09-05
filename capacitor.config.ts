import type { CapacitorConfig } from '@capacitor/cli';

/**
 * DeYoung native app shell (Android / iOS via Capacitor).
 *
 * The web app at https://deeyoung-production-72ef.up.railway.app is a full
 * PWA; Capacitor wraps it in a native binary that ships through the Play
 * Store / App Store while the UI, studio and queue keep updating server-side
 * (no app re-releases needed for content or feature changes).
 *
 * Build (one-time per platform, requires Android Studio / Xcode):
 *   npm i -D @capacitor/cli @capacitor/core @capacitor/android @capacitor/ios
 *   npx cap init "DeYoung" site.deyoung.app --web-dir=public
 *   npx cap add android && npx cap add ios
 *   npx cap open android      // then Build > Generate Signed Bundle
 * Docs: docs/NATIVE_APP.md
 */
const config: CapacitorConfig = {
  appId: 'site.deyoung.app',
  appName: 'DeYoung',
  webDir: 'public',
  server: {
    url: 'https://deeyoung-production-72ef.up.railway.app',
    cleartext: false,
  },
  android: {
    backgroundColor: '#17171A',
    allowMixedContent: false,
  },
  ios: {
    contentSource: 'https://deeyoung-production-72ef.up.railway.app',
  },
};

export default config;
