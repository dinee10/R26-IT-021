import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../theme/app_colors.dart';
import '../widgets/app_buttons.dart';
import '../widgets/user_avatar.dart';
import 'edit_profile_page.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage> {
  bool _signingOut = false;

  Future<void> _openEditProfile() async {
    final updated = await Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => const EditProfilePage(),
      ),
    );

    if (updated == true && mounted) {
      setState(() {});
    }
  }

  Future<void> _signOut() async {
    setState(() => _signingOut = true);

    try {
      if (!kIsWeb) {
        await GoogleSignIn().signOut();
      }
      await FirebaseAuth.instance.signOut();
    } on FirebaseAuthException catch (error) {
      _showMessage(error.message ?? 'Could not log out.');
    } catch (_) {
      _showMessage('Could not log out. Please try again.');
    } finally {
      if (mounted) {
        setState(() => _signingOut = false);
      }
    }
  }

  void _showMessage(String message) {
    if (!mounted) {
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;
    final provider = user?.providerData.isNotEmpty == true
        ? user!.providerData.first.providerId
        : 'password';

    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        centerTitle: false,
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
          children: [
            Center(child: UserAvatar(user: user, radius: 52)),
            const SizedBox(height: 18),
            Center(
              child: Text(
                user?.displayName?.isNotEmpty == true
                    ? user!.displayName!
                    : 'AyurPlant User',
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: AppColors.text,
                  fontSize: 24,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
            const SizedBox(height: 6),
            Center(
              child: Text(
                user?.email ?? 'No email connected',
                style: const TextStyle(
                  color: AppColors.muted,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 28),
            ProfileInfoRow(
              icon: Icons.person_outline_rounded,
              label: 'Full Name',
              value: user?.displayName?.isNotEmpty == true
                  ? user!.displayName!
                  : 'Not set',
            ),
            const SizedBox(height: 10),
            ProfileInfoRow(
              icon: Icons.mail_outline_rounded,
              label: 'Email Address',
              value: user?.email ?? 'No email connected',
            ),
            const SizedBox(height: 10),
            ProfileInfoRow(
              icon: Icons.verified_user_outlined,
              label: 'Login Provider',
              value: _providerLabel(provider),
            ),
            const SizedBox(height: 10),
            ProfileInfoRow(
              icon: Icons.key_rounded,
              label: 'Firebase UID',
              value: user?.uid ?? '-',
            ),
            const SizedBox(height: 28),
            PrimaryButton(
              label: 'Edit Profile',
              icon: Icons.edit_rounded,
              onPressed: _openEditProfile,
            ),
            const SizedBox(height: 14),
            OutlinedButton.icon(
              onPressed: _signingOut ? null : _signOut,
              icon: const Icon(Icons.logout_rounded),
              label: Text(_signingOut ? 'Logging Out' : 'Log Out'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.danger,
                disabledForegroundColor: AppColors.danger.withValues(
                  alpha: 0.55,
                ),
                side: const BorderSide(color: Color(0xFFF0B7AC)),
                minimumSize: const Size.fromHeight(52),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _providerLabel(String providerId) {
    return switch (providerId) {
      'google.com' => 'Google',
      'password' => 'Email and password',
      _ => providerId,
    };
  }
}

class ProfileInfoRow extends StatelessWidget {
  const ProfileInfoRow({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(
                    color: AppColors.muted,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: AppColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
