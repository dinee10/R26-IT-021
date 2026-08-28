import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../widgets/app_buttons.dart';
import '../widgets/auth_layout.dart';
import 'login_page.dart';

class WelcomePage extends StatelessWidget {
  const WelcomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: BackgroundShell(
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(28, 40, 28, 28),
            child: Column(
              children: [
                const Spacer(flex: 3),
                Image.asset(
                  'assets/images/logo_transparent.png',
                  width: 88,
                  height: 88,
                ),
                const SizedBox(height: 18),
                const Text(
                  'AyurPlant',
                  style: TextStyle(
                    color: AppColors.text,
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'SRI LANKAN MEDICINAL PLANTS',
                  style: TextStyle(
                    color: AppColors.primary,
                    fontSize: 12,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 28),
                const Text(
                  'Identify - Learn - Heal',
                  style: TextStyle(
                    color: AppColors.muted,
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const Spacer(flex: 4),
                PrimaryButton(
                  label: 'Get Started',
                  icon: Icons.chevron_right_rounded,
                  onPressed: () => Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (_) => const LoginPage(),
                    ),
                  ),
                ),
                const SizedBox(height: 20),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text(
                      'Already have an account? ',
                      style: TextStyle(
                        color: AppColors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    TextButton(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => const LoginPage(),
                        ),
                      ),
                      child: const Text('Log in'),
                    ),
                  ],
                ),
                const Spacer(),
                const Text(
                  'THE DIGITAL HERBARIUM OF SRI LANKA',
                  style: TextStyle(
                    color: Color(0xFFC5CDC6),
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
