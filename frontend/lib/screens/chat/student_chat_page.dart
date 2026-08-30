import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../widgets/persona_chat_scaffold.dart';

class StudentChatPage extends StatelessWidget {
  const StudentChatPage({super.key});

  static const _accent = Color(0xFF8B5CF6);

  @override
  Widget build(BuildContext context) {
    return PersonaChatScaffold(
      personaLabel: "Student",
      userTypeKey: "student",
      accentColor: _accent,
      icon: Icons.school_outlined,
      greeting: "Ask about medicinal plants\nExplanations include the 'why', good for study notes.",
      infoBanner: Container(
        width: double.infinity,
        color: _accent.withOpacity(0.08),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: const Row(
          children: [
            Icon(Icons.menu_book_outlined, size: 16, color: _accent),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                "Answers explain underlying concepts, not just facts — useful for coursework.",
                style: TextStyle(fontSize: 12, color: AppColors.text),
              ),
            ),
          ],
        ),
      ),
    );
  }
}