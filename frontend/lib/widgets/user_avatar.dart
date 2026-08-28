import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

class UserAvatar extends StatelessWidget {
  const UserAvatar({
    super.key,
    required this.user,
    required this.radius,
  });

  final User? user;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final photoUrl = user?.photoURL;
    final initials = _initials(user?.displayName ?? user?.email);

    return Stack(
      clipBehavior: Clip.none,
      children: [
        ClipOval(
          child: Container(
            width: radius * 2,
            height: radius * 2,
            color: const Color(0xFFEAF7ED),
            child: photoUrl == null
                ? _InitialsText(initials: initials, radius: radius)
                : Image.network(
                    photoUrl,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) {
                      return _InitialsText(initials: initials, radius: radius);
                    },
                  ),
          ),
        ),
        Positioned(
          right: 2,
          bottom: 2,
          child: Container(
            width: radius * 0.34,
            height: radius * 0.34,
            decoration: BoxDecoration(
              color: AppColors.primary,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white, width: 2),
            ),
          ),
        ),
      ],
    );
  }

  String _initials(String? value) {
    if (value == null || value.trim().isEmpty) {
      return 'A';
    }

    final parts = value.trim().split(RegExp(r'\s+'));
    if (parts.length == 1) {
      return parts.first.substring(0, 1).toUpperCase();
    }

    return '${parts.first.substring(0, 1)}${parts.last.substring(0, 1)}'
        .toUpperCase();
  }
}

class _InitialsText extends StatelessWidget {
  const _InitialsText({
    required this.initials,
    required this.radius,
  });

  final String initials;
  final double radius;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text(
        initials,
        style: TextStyle(
          color: AppColors.primary,
          fontSize: radius * 0.58,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
