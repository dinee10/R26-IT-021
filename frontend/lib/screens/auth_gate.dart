import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'home_shell.dart';
import 'splash_screen.dart';
import 'welcome_page.dart';

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const SplashScreen();
        }

        if (snapshot.hasData) {
          return const HomeShell();
        }

        return const WelcomePage();
      },
    );
  }
}
