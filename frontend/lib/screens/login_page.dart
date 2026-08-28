import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../widgets/app_buttons.dart';
import '../widgets/app_text_field.dart';
import '../widgets/auth_layout.dart';
import 'signup_page.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _signInWithEmail() async {
    await _runAuthAction(() {
      return FirebaseAuth.instance.signInWithEmailAndPassword(
        email: _emailController.text.trim(),
        password: _passwordController.text,
      );
    });
  }

  Future<void> _signInWithGoogle() async {
    await _runAuthAction(() async {
      if (kIsWeb) {
        return FirebaseAuth.instance.signInWithPopup(GoogleAuthProvider());
      }

      final googleUser = await GoogleSignIn().signIn();
      if (googleUser == null) {
        return null;
      }

      final googleAuth = await googleUser.authentication;
      final credential = GoogleAuthProvider.credential(
        accessToken: googleAuth.accessToken,
        idToken: googleAuth.idToken,
      );

      return FirebaseAuth.instance.signInWithCredential(credential);
    });
  }

  Future<void> _resetPassword() async {
    final email = _emailController.text.trim();
    if (email.isEmpty) {
      _showMessage('Enter your email address first.');
      return;
    }

    await _runAuthAction(() {
      return FirebaseAuth.instance.sendPasswordResetEmail(email: email);
    }, successMessage: 'Password reset email sent.');
  }

  Future<void> _runAuthAction(
    Future<dynamic> Function() action, {
    String? successMessage,
  }) async {
    setState(() => _loading = true);

    try {
      final result = await action();
      if (successMessage != null) {
        _showMessage(successMessage);
      } else if (result != null && mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
      }
    } on FirebaseAuthException catch (error) {
      _showMessage(error.message ?? 'Authentication failed.');
    } catch (_) {
      _showMessage('Something went wrong. Please try again.');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
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
    return AuthScaffold(
      title: 'Welcome back',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SocialButton(
            label: 'Continue with Google',
            leading: const GoogleLogoMark(),
            onPressed: _loading ? null : _signInWithGoogle,
          ),
          const SizedBox(height: 28),
          const DividerLabel(label: 'OR'),
          const SizedBox(height: 28),
          const FieldLabel('Email Address'),
          AppTextField(
            controller: _emailController,
            hintText: 'name@example.com',
            icon: Icons.mail_outline_rounded,
            keyboardType: TextInputType.emailAddress,
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const FieldLabel('Password'),
              TextButton(
                onPressed: _loading ? null : _resetPassword,
                child: const Text('Forgot password?'),
              ),
            ],
          ),
          AppTextField(
            controller: _passwordController,
            hintText: 'Password',
            icon: Icons.lock_outline_rounded,
            obscureText: _obscurePassword,
            suffixIcon: IconButton(
              onPressed: () {
                setState(() => _obscurePassword = !_obscurePassword);
              },
              icon: Icon(
                _obscurePassword
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
              ),
            ),
          ),
          const SizedBox(height: 28),
          PrimaryButton(
            label: _loading ? 'Please wait' : 'Log In',
            icon: Icons.arrow_forward_rounded,
            onPressed: _loading ? null : _signInWithEmail,
          ),
          const SizedBox(height: 72),
          AccountSwitchRow(
            prompt: "Don't have an account?",
            action: 'Sign Up',
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => const SignUpPage(),
              ),
            ),
          ),
          const SizedBox(height: 18),
          const TermsText(),
        ],
      ),
    );
  }
}
