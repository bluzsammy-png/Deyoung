# DeYoung Native App — research findings & build path

Date: 2026-09-05. Written by the build agent. Facts only; nothing aspirational.

## 1. About "AppDeploy API"

You asked to "use AppDeploy api and create a native app". Research result:

- **No verifiable service called "AppDeploy" exists** among established app
  deployment/build APIs (searched: app deployment APIs, native app builders,
  CI app-upload services — closest names are unrelated products like App
  Builder / Appinstitute / lastapp, none expose an API we can call).
- We will not integrate a service we cannot verify exists — that would risk
  your credentials and your users' data.

**What you get instead (and why it is the better path):**

| Option | What it is | Status here |
|---|---|---|
| PWA (installable website) | Users on Android/Chrome iOS "Add to Home Screen" — full-screen, icon, splash, offline shell | ✅ Already shipped: `public/manifest.webmanifest`, icons, theme color |
| Capacitor native shell | Wraps the live site in a real Android/iOS binary for the Play Store / App Store | ✅ Config committed: `capacitor.config.ts` — build steps below |
| Google Play via TWA | Publish the PWA directly with a Digital Asset Links check | Documented, needs the deyoung.site domain on Railway first |

This is the same approach used by production SaaS products that want
store presence without maintaining two codebases.

## 2. Build the Android app (one afternoon, free)

Prereqs: Android Studio (includes SDK), JDK 17, Node 20+.

```bash
npm i -D @capacitor/cli && npm i @capacitor/core @capacitor/android
npx cap add android
npx cap sync android
npx cap open android
# In Android Studio: Build > Generate Signed Bundle / APK
# - create a keystore (keep it + passwords safe — losing it means new store listing)
# - upload the .aab to Play Console ($25 one-time Google fee)
```

## 3. Build the iOS app (needs a Mac + Apple Developer account, $99/yr)

```bash
npm i @capacitor/ios
npx cap add ios
npx cap sync ios
npx cap open ios
# In Xcode: Product > Archive > Distribute App
```

## 4. Why the shell approach is right for DeYoung

- The studio, queue, models, payments and support chat are **server-rendered**
  — updates ship to every user instantly, no app-store review delays.
- The native layer adds: store presence, push notifications (later, via
  Capacitor Push plugin), home-screen icon, splash screen.
- Same auth (HTTP-only cookie) works inside the shell because the server URL
  is the production Railway app over HTTPS.

## 5. Honest limits

- Apple can reject thin wrappers. If that happens, the fallback is a
  Trusted Web Activity on Android (Play Store accepts PWAs readily) plus the
  PWA on iOS until feature work justifies true native screens.
- Push notifications and biometric login are real next steps (both are
  official Capacitor plugins, both need the native shell built first).
