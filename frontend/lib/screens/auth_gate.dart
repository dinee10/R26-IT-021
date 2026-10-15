import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'home_shell.dart';
import 'login_page.dart';
import 'onboarding_page.dart';
import 'splash_screen.dart';
import 'welcome_page.dart';

/// Chooses the correct entry screen without changing the Firebase login flow.
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> {
  static const _onboardingKey = 'ayurplant_onboarding_seen_v1';

  late final Future<bool> _seenOnboarding;
  bool? _seenOverride;

  @override
  void initState() {
    super.initState();
    _seenOnboarding = _readOnboardingPreference();
  }

  Future<bool> _readOnboardingPreference() async {
    try {
      final preferences = await SharedPreferences.getInstance();
      return preferences.getBool(_onboardingKey) ?? false;
    } catch (_) {
      // If local storage is unavailable, do not block authentication.
      return true;
    }
  }

  Future<void> _finishOnboarding({required bool goToLogin}) async {
    try {
      final preferences = await SharedPreferences.getInstance();
      await preferences.setBool(_onboardingKey, true);
    } catch (_) {
      // The app remains usable even if the preference cannot be saved.
    }

    if (!mounted) return;

    // The normal Welcome page remains the first route for signed-out users.
    setState(() => _seenOverride = true);

    if (goToLogin) {
      // The existing LoginPage pops to the first route after successful login.
      // That first route is this AuthGate, which will then display HomeShell.
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(builder: (_) => const LoginPage()),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, authSnapshot) {
        if (authSnapshot.connectionState == ConnectionState.waiting) {
          return const SplashScreen();
        }

        if (authSnapshot.hasData) {
          return const HomeShell();
        }

        // Show onboarding to signed-out users only on their first visit.
        return FutureBuilder<bool>(
          future: _seenOnboarding,
          builder: (context, preferenceSnapshot) {
            if (_seenOverride == null &&
                preferenceSnapshot.connectionState != ConnectionState.done) {
              return const SplashScreen();
            }

            final hasSeenOnboarding =
                _seenOverride ?? preferenceSnapshot.data ?? true;

            if (hasSeenOnboarding) {
              return const WelcomePage();
            }

            return OnboardingPage(
              onGetStarted: () => _finishOnboarding(goToLogin: true),
              onSkip: () => _finishOnboarding(goToLogin: false),
            );
          },
        );
      },
    );
  }
}
